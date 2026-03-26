import SwiftUI

/// Cached async image that stores downloaded images in NSCache.
struct CachedAsyncImage<Placeholder: View>: View {
    let url: URL?
    let placeholder: () -> Placeholder

    @State private var image: UIImage?
    @State private var isLoading = false

    init(url: URL?, @ViewBuilder placeholder: @escaping () -> Placeholder) {
        self.url = url
        self.placeholder = placeholder
    }

    var body: some View {
        if let image {
            Image(uiImage: image)
                .resizable()
        } else {
            placeholder()
                .task(id: url) {
                    await loadImage()
                }
        }
    }

    private func loadImage() async {
        guard let url, !isLoading else { return }

        if let cached = ImageCacheStore.shared.get(url) {
            image = cached
            return
        }

        isLoading = true
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            if let uiImage = UIImage(data: data) {
                ImageCacheStore.shared.set(uiImage, for: url)
                image = uiImage
            }
        } catch {
            // Silently fail, placeholder remains
        }
        isLoading = false
    }
}

/// In-memory image cache using NSCache.
final class ImageCacheStore: @unchecked Sendable {
    static let shared = ImageCacheStore()

    private let cache = NSCache<NSURL, UIImage>()

    private init() {
        cache.countLimit = 50
    }

    func get(_ url: URL) -> UIImage? {
        cache.object(forKey: url as NSURL)
    }

    func set(_ image: UIImage, for url: URL) {
        cache.setObject(image, forKey: url as NSURL)
    }
}
