import Foundation

let useApple = CommandLine.arguments.contains("--apple")

let provider: any ModelProvider
#if canImport(FoundationModels)
if useApple {
    if #available(macOS 26.0, *) {
        print("Using Apple Foundation Models (on-device)")
        provider = FoundationModelProvider()
    } else {
        print("macOS 26 required for Foundation Models, using stub")
        provider = StubProvider()
    }
} else {
    print("Using stub provider (pass --apple to use Foundation Models)")
    provider = StubProvider()
}
#else
if useApple {
    print("FoundationModels not available on this platform, using stub")
}
provider = StubProvider()
#endif

let server = SidecarServer(provider: provider)
try await server.start()
