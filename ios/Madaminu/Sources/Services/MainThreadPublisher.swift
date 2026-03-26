import Foundation

/// Ensures a block runs on the main thread.
/// If already on main thread, executes synchronously.
/// If on background thread, dispatches async to main.
@inline(__always)
func ensureMainThread(_ block: @escaping @Sendable () -> Void) {
    if Thread.isMainThread {
        block()
    } else {
        DispatchQueue.main.async(execute: block)
    }
}
