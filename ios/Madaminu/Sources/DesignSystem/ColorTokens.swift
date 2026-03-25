import SwiftUI

public extension Color {
    // MARK: - Primary
    static let mdPrimary = Color(hex: "C9A96E")
    static let mdPrimaryLight = Color(hex: "DFC490")
    static let mdPrimaryDark = Color(hex: "A88B4A")

    // MARK: - Background
    static let mdBackground = Color(hex: "1A1A2E")
    static let mdBackgroundSecondary = Color(hex: "16213E")
    static let mdSurface = Color(hex: "0F3460")
    static let mdSurfaceLight = Color(hex: "1A4A7A")

    // MARK: - Text
    static let mdTextPrimary = Color(hex: "E8E8E8")
    static let mdTextSecondary = Color(hex: "A0A0B0")
    static let mdTextMuted = Color(hex: "6B6B7B")

    // MARK: - Accent
    static let mdAccent = Color(hex: "E94560")
    static let mdAccentLight = Color(hex: "FF6B81")

    // MARK: - Semantic
    static let mdSuccess = Color(hex: "4CAF50")
    static let mdWarning = Color(hex: "FFC107")
    static let mdError = Color(hex: "E94560")
    static let mdInfo = Color(hex: "5DADE2")

    // MARK: - Game Phase
    static let mdInvestigation = Color(hex: "5DADE2")
    static let mdDiscussion = Color(hex: "C9A96E")
    static let mdVoting = Color(hex: "E94560")
}

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let r = Double((int >> 16) & 0xFF) / 255.0
        let g = Double((int >> 8) & 0xFF) / 255.0
        let b = Double(int & 0xFF) / 255.0
        self.init(red: r, green: g, blue: b)
    }
}
