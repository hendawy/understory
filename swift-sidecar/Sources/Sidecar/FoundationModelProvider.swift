import Foundation

#if canImport(FoundationModels)
import FoundationModels

@available(macOS 26.0, *)
struct FoundationModelProvider: ModelProvider {
    private let session: LanguageModelSession

    init() {
        self.session = LanguageModelSession()
    }

    func complete(messages: [Message], schema: [String: AnyCodable]?) async throws -> String {
        let prompt = messages.map { "\($0.role): \($0.content)" }.joined(separator: "\n")
        let response = try await session.respond(to: prompt)
        return response.content
    }

    func availableModels() async -> [String] {
        let model = SystemLanguageModel.default
        guard model.availability == .available else { return [] }
        return ["apple-on-device"]
    }

    static func isAvailable() -> Bool {
        SystemLanguageModel.default.availability == .available
    }
}
#endif
