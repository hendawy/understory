import Foundation
import Testing
@testable import Sidecar

@Suite struct RoutingTests {
    let encoder = JSONEncoder()
    let decoder = JSONDecoder()
    let server = SidecarServer(provider: StubProvider(fixedReply: "test reply"))

    @Test func healthz() async {
        let (status, body) = await server.route(method: "GET", path: "/healthz", body: nil)
        #expect(status == 200)
        let text = String(data: body, encoding: .utf8)
        #expect(text?.contains("ok") == true)
    }

    @Test func models() async throws {
        let (status, body) = await server.route(method: "GET", path: "/models", body: nil)
        #expect(status == 200)
        let resp = try decoder.decode(ModelsResponse.self, from: body)
        #expect(resp.models == ["stub-model"])
    }

    @Test func completeSuccess() async throws {
        let req = CompleteRequest(
            model: "stub-model",
            messages: [Message(role: "user", content: "hello")],
            schema: nil
        )
        let reqData = try encoder.encode(req)
        let (status, body) = await server.route(method: "POST", path: "/complete", body: reqData)
        #expect(status == 200)
        let resp = try decoder.decode(CompleteResponse.self, from: body)
        #expect(resp.content == "test reply")
    }

    @Test func completeMissingBody() async {
        let (status, _) = await server.route(method: "POST", path: "/complete", body: nil)
        #expect(status == 400)
    }

    @Test func completeInvalidJSON() async {
        let (status, _) = await server.route(method: "POST", path: "/complete", body: Data("nope".utf8))
        #expect(status == 400)
    }

    @Test func notFound() async {
        let (status, _) = await server.route(method: "GET", path: "/nope", body: nil)
        #expect(status == 404)
    }
}
