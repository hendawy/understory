import Foundation
import Testing
@testable import Sidecar

@Suite struct StubProviderTests {
    @Test func fixedReply() async throws {
        let provider = StubProvider(fixedReply: "fixed")
        let result = try await provider.complete(messages: [Message(role: "user", content: "x")], schema: nil)
        #expect(result == "fixed")
    }

    @Test func echoesLastMessage() async throws {
        let provider = StubProvider()
        let result = try await provider.complete(
            messages: [
                Message(role: "user", content: "first"),
                Message(role: "user", content: "second"),
            ],
            schema: nil
        )
        #expect(result == "stub: second")
    }

    @Test func availableModels() async {
        let models = await StubProvider().availableModels()
        #expect(models == ["stub-model"])
    }
}
