import Foundation
import Testing
@testable import Sidecar

@Suite struct DTOTests {
    let encoder = JSONEncoder()
    let decoder = JSONDecoder()

    @Test func completeRequestDecodes() throws {
        let json = """
        {"model":"test","messages":[{"role":"user","content":"hi"}],"schema":null}
        """
        let req = try decoder.decode(CompleteRequest.self, from: Data(json.utf8))
        #expect(req.model == "test")
        #expect(req.messages.count == 1)
        #expect(req.messages[0].role == "user")
        #expect(req.messages[0].content == "hi")
        #expect(req.schema == nil)
    }

    @Test func completeRequestWithSchema() throws {
        let json = """
        {"model":"m","messages":[],"schema":{"type":"object","properties":{"tool":{"type":"string"}}}}
        """
        let req = try decoder.decode(CompleteRequest.self, from: Data(json.utf8))
        #expect(req.schema != nil)
        #expect(req.schema?["type"] == AnyCodable.string("object"))
    }

    @Test func completeResponseEncodes() throws {
        let resp = CompleteResponse(content: "hello")
        let data = try encoder.encode(resp)
        let dict = try decoder.decode([String: String].self, from: data)
        #expect(dict["content"] == "hello")
    }

    @Test func modelsResponseEncodes() throws {
        let resp = ModelsResponse(models: ["a", "b"])
        let data = try encoder.encode(resp)
        let dict = try decoder.decode([String: [String]].self, from: data)
        #expect(dict["models"] == ["a", "b"])
    }

    @Test func messageRoundTrip() throws {
        let msg = Message(role: "assistant", content: "done")
        let data = try encoder.encode(msg)
        let decoded = try decoder.decode(Message.self, from: data)
        #expect(decoded.role == "assistant")
        #expect(decoded.content == "done")
    }
}
