// swift-tools-version: 6.1

import PackageDescription

let package = Package(
    name: "Madaminu",
    platforms: [
        .iOS(.v17)
    ],
    products: [
        .library(
            name: "DesignSystem",
            targets: ["DesignSystem"]
        ),
        .library(
            name: "MadaminuKit",
            targets: ["MadaminuKit"]
        ),
    ],
    targets: [
        .target(
            name: "DesignSystem",
            path: "Sources/DesignSystem"
        ),
        .target(
            name: "MadaminuKit",
            dependencies: ["DesignSystem"],
            path: "Sources",
            exclude: ["DesignSystem", "App"],
            sources: ["Models", "Services", "Views"]
        ),
    ]
)
