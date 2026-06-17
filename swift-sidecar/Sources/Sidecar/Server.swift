import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// Minimal HTTP server using NWListener would be ideal but requires Network framework.
/// For Swift 5.10 CLI compatibility, we use a raw socket approach via Foundation.
final class SidecarServer: Sendable {
    let host: String
    let port: UInt16
    let provider: any ModelProvider

    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    init(host: String = "127.0.0.1", port: UInt16 = 8081, provider: any ModelProvider) {
        self.host = host
        self.port = port
        self.provider = provider
    }

    /// Route a request to the appropriate handler. Public for testing.
    func route(method: String, path: String, body: Data?) async -> (status: Int, body: Data) {
        switch (method, path) {
        case ("GET", "/healthz"):
            return handleHealthz()
        case ("GET", "/models"):
            return await handleModels()
        case ("POST", "/complete"):
            return await handleComplete(body: body)
        default:
            return (404, Data("{\"error\":\"not found\"}".utf8))
        }
    }

    private func handleHealthz() -> (status: Int, body: Data) {
        (200, Data("{\"status\":\"ok\"}".utf8))
    }

    private func handleModels() async -> (status: Int, body: Data) {
        let models = await provider.availableModels()
        let response = ModelsResponse(models: models)
        do {
            let data = try encoder.encode(response)
            return (200, data)
        } catch {
            return (500, Data("{\"error\":\"encode failed\"}".utf8))
        }
    }

    private func handleComplete(body: Data?) async -> (status: Int, body: Data) {
        guard let body else {
            return (400, Data("{\"error\":\"missing body\"}".utf8))
        }
        let request: CompleteRequest
        do {
            request = try decoder.decode(CompleteRequest.self, from: body)
        } catch {
            return (400, Data("{\"error\":\"invalid JSON\"}".utf8))
        }
        do {
            let content = try await provider.complete(messages: request.messages, schema: request.schema)
            let response = CompleteResponse(content: content)
            let data = try encoder.encode(response)
            return (200, data)
        } catch {
            return (500, Data("{\"error\":\"\(error)\"}".utf8))
        }
    }

    /// Start listening. Blocks until cancelled.
    func start() async throws {
        let socket = socket(AF_INET, SOCK_STREAM, 0)
        guard socket >= 0 else { throw SidecarError.socketFailed }

        var yes: Int32 = 1
        setsockopt(socket, SOL_SOCKET, SO_REUSEADDR, &yes, socklen_t(MemoryLayout<Int32>.size))

        var addr = sockaddr_in()
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = port.bigEndian
        addr.sin_addr.s_addr = inet_addr(host)

        let bindResult = withUnsafePointer(to: &addr) { ptr in
            ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) { sockPtr in
                Darwin.bind(socket, sockPtr, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        guard bindResult == 0 else { throw SidecarError.bindFailed }

        listen(socket, 128)
        print("Sidecar listening on \(host):\(port)")

        while true {
            let client = accept(socket, nil, nil)
            guard client >= 0 else { continue }

            Task { [self] in
                await self.handleClient(client)
            }
        }
    }

    private func handleClient(_ fd: Int32) async {
        var buffer = [UInt8](repeating: 0, count: 65536)
        let bytesRead = read(fd, &buffer, buffer.count)
        guard bytesRead > 0 else { close(fd); return }

        let raw = String(bytes: buffer[..<bytesRead], encoding: .utf8) ?? ""
        let (method, path, body) = parseHTTP(raw)
        let (status, responseBody) = await route(method: method, path: path, body: body)

        let statusText = status == 200 ? "OK" : status == 400 ? "Bad Request" : status == 404 ? "Not Found" : "Error"
        let header = "HTTP/1.1 \(status) \(statusText)\r\nContent-Type: application/json\r\nContent-Length: \(responseBody.count)\r\nConnection: close\r\n\r\n"
        var response = Data(header.utf8)
        response.append(responseBody)
        response.withUnsafeBytes { ptr in
            _ = write(fd, ptr.baseAddress, response.count)
        }
        close(fd)
    }

    private func parseHTTP(_ raw: String) -> (method: String, path: String, body: Data?) {
        let parts = raw.split(separator: "\r\n\r\n", maxSplits: 1)
        let headerSection = String(parts[0])
        let body = parts.count > 1 ? Data(String(parts[1]).utf8) : nil

        let firstLine = headerSection.split(separator: "\r\n").first ?? ""
        let tokens = firstLine.split(separator: " ")
        let method = tokens.count > 0 ? String(tokens[0]) : ""
        let path = tokens.count > 1 ? String(tokens[1]) : ""

        return (method, path, body)
    }
}

enum SidecarError: Error {
    case socketFailed
    case bindFailed
}
