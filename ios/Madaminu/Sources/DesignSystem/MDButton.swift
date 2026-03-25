import SwiftUI

public enum MDButtonStyle: Sendable {
    case primary
    case secondary
    case danger
    case ghost
}

public struct MDButton: View {
    let title: String
    let style: MDButtonStyle
    let isLoading: Bool
    let action: () -> Void

    public init(
        _ title: String,
        style: MDButtonStyle = .primary,
        isLoading: Bool = false,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.style = style
        self.isLoading = isLoading
        self.action = action
    }

    public var body: some View {
        Button(action: action) {
            HStack(spacing: Spacing.xs) {
                if isLoading {
                    ProgressView()
                        .tint(textColor)
                }
                Text(title)
                    .font(.mdHeadline)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, Spacing.sm)
            .padding(.horizontal, Spacing.md)
            .background(backgroundColor)
            .foregroundStyle(textColor)
            .clipShape(RoundedRectangle(cornerRadius: CornerRadius.md))
            .overlay(
                RoundedRectangle(cornerRadius: CornerRadius.md)
                    .stroke(borderColor, lineWidth: style == .ghost ? 1 : 0)
            )
        }
        .disabled(isLoading)
    }

    private var backgroundColor: Color {
        switch style {
        case .primary: .mdPrimary
        case .secondary: .mdSurface
        case .danger: .mdAccent
        case .ghost: .clear
        }
    }

    private var textColor: Color {
        switch style {
        case .primary: .mdBackground
        case .secondary: .mdTextPrimary
        case .danger: .mdTextPrimary
        case .ghost: .mdPrimary
        }
    }

    private var borderColor: Color {
        switch style {
        case .ghost: .mdPrimary
        default: .clear
        }
    }
}
