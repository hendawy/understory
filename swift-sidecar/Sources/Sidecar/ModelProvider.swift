import Foundation

struct Message: Codable, Sendable {
    let role: String
    let content: String
}

struct CompleteRequest: Codable, Sendable {
    let model: String
    let messages: [Message]
    let schema: [String: AnyCodable]?
}

struct CompleteResponse: Codable, Sendable {
    let content: String
}

struct ModelsResponse: Codable, Sendable {
    let models: [String]
}

/// The model layer protocol — real FoundationModels or a stub.
protocol ModelProvider: Sendable {
    func complete(messages: [Message], schema: [String: AnyCodable]?) async throws -> String
    func availableModels() async -> [String]
}
