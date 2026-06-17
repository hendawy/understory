// swift-tools-version: 6.2

import PackageDescription

let package = Package(
    name: "understory-sidecar",
    platforms: [.macOS(.v26)],
    targets: [
        .executableTarget(
            name: "Sidecar",
            path: "Sources/Sidecar"
        ),
        .testTarget(
            name: "SidecarTests",
            dependencies: ["Sidecar"],
            path: "Tests/SidecarTests"
        ),
    ]
)
