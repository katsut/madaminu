import DesignSystem
import SwiftUI

struct NotebookView: View {
    @Bindable var viewModel: GameViewModel

    var body: some View {
        ZStack {
            Color.mdBackground
                .ignoresSafeArea()

            ScrollView {
                VStack(spacing: Spacing.md) {
                    header
                    characterSection
                    objectiveSection
                    evidenceSection
                    notesSection
                }
                .padding(Spacing.lg)
            }
        }
    }

    private var header: some View {
        HStack {
            Text("個人手帳")
                .font(.mdTitle)
                .foregroundStyle(Color.mdPrimary)
            Spacer()
        }
    }

    private var characterSection: some View {
        MDCard {
            VStack(alignment: .leading, spacing: Spacing.sm) {
                Label("キャラクター情報", systemImage: "person.fill")
                    .font(.mdHeadline)
                    .foregroundStyle(Color.mdPrimary)

                if let role = viewModel.myRole {
                    HStack {
                        Text("役割")
                            .font(.mdCaption)
                            .foregroundStyle(Color.mdTextMuted)
                        Spacer()
                        Text(roleDisplayName(role))
                            .font(.mdCallout)
                            .foregroundStyle(Color.mdTextPrimary)
                    }
                }

                if let secret = viewModel.mySecretInfo {
                    VStack(alignment: .leading, spacing: Spacing.xxs) {
                        Text("秘密")
                            .font(.mdCaption)
                            .foregroundStyle(Color.mdAccent)
                        Text(secret)
                            .font(.mdBody)
                            .foregroundStyle(Color.mdTextPrimary)
                    }
                }
            }
        }
    }

    private var objectiveSection: some View {
        Group {
            if let objective = viewModel.myObjective {
                MDCard {
                    VStack(alignment: .leading, spacing: Spacing.xs) {
                        Label("個人目的", systemImage: "target")
                            .font(.mdHeadline)
                            .foregroundStyle(Color.mdWarning)

                        Text(objective)
                            .font(.mdBody)
                            .foregroundStyle(Color.mdTextPrimary)
                    }
                }
            }
        }
    }

    private var evidenceSection: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            HStack {
                Label("証拠カード", systemImage: "doc.text.magnifyingglass")
                    .font(.mdHeadline)
                    .foregroundStyle(Color.mdInfo)

                Spacer()

                Text("\(viewModel.evidences.count)件")
                    .font(.mdCaption)
                    .foregroundStyle(Color.mdTextMuted)
            }

            if viewModel.evidences.isEmpty {
                MDCard {
                    Text("まだ証拠はありません")
                        .font(.mdBody)
                        .foregroundStyle(Color.mdTextMuted)
                        .frame(maxWidth: .infinity, alignment: .center)
                }
            } else {
                ForEach(viewModel.evidences) { evidence in
                    MDCard {
                        VStack(alignment: .leading, spacing: Spacing.xxs) {
                            Text(evidence.title)
                                .font(.mdHeadline)
                                .foregroundStyle(Color.mdTextPrimary)
                            Text(evidence.content)
                                .font(.mdBody)
                                .foregroundStyle(Color.mdTextSecondary)
                        }
                    }
                    .transition(.asymmetric(insertion: .slide, removal: .opacity))
                }
            }
        }
        .animation(.easeInOut, value: viewModel.evidences.count)
    }

    private var notesSection: some View {
        VStack(alignment: .leading, spacing: Spacing.sm) {
            Label("メモ", systemImage: "pencil.and.outline")
                .font(.mdHeadline)
                .foregroundStyle(Color.mdTextSecondary)

            MDTextEditor(label: "", text: $viewModel.notes, minHeight: 120)
        }
    }

    private func roleDisplayName(_ role: String) -> String {
        switch role {
        case "criminal": "犯人"
        case "witness": "目撃者"
        case "related": "関係者"
        case "innocent": "一般人"
        default: role
        }
    }
}
