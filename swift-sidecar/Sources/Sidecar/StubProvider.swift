import Foundation

/// Stub provider for testing. Echoes back a canned response or the last message content.
/// Replace with FoundationModelProvider once Xcode 26 + macOS 26 SDK is available.
struct StubProvider: ModelProvider {
    let fixedReply: String?

    init(fixedReply: String? = nil) {
        self.fixedReply = fixedReply
    }

    func complete(messages: [Message], schema: [String: AnyCodable]?) async throws -> String {
        if let reply = fixedReply {
            return reply
        }
        let last = messages.last?.content ?? ""
        return "stub: \(last)"
    }

    func availableModels() async -> [String] {
        ["stub-model"]
    }
}
