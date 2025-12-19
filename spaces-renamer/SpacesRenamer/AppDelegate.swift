import Cocoa
import AppKit
import SwiftUI

@main
class AppDelegate: NSObject, NSApplicationDelegate {
    var statusBarItem: NSStatusItem?
    var spacesManager: SpacesManager?
    var overlayWindows: [NSWindow] = []

    func applicationDidFinishLaunching(_ aNotification: Notification) {
        // Criar item na barra de menu
        statusBarItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        if let button = statusBarItem?.button {
            button.image = NSImage(systemSymbolName: "square.grid.2x2", accessibilityDescription: "Spaces Renamer")
            button.action = #selector(showMenu)
        }
        
        // Inicializar gerenciador de spaces
        spacesManager = SpacesManager()
        spacesManager?.delegate = self
        
        // Solicitar permissões de acessibilidade
        requestAccessibilityPermissions()
        
        // Iniciar monitoramento
        startMonitoring()
    }
    
    @objc func showMenu() {
        let menu = NSMenu()
        
        menu.addItem(NSMenuItem(title: "Gerenciar Spaces", action: #selector(openPreferences), keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Sair", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        
        statusBarItem?.menu = menu
        statusBarItem?.button?.performClick(nil)
    }
    
    @objc func openPreferences() {
        // Criar janela de preferências programaticamente com SwiftUI
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 500, height: 600),
            styleMask: [.titled, .closable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        
        window.title = "Gerenciar Spaces"
        window.center()
        
        guard let manager = spacesManager else { return }
        let preferencesView = PreferencesView(spacesManager: manager)
        let hostingView = NSHostingView(rootView: preferencesView)
        hostingView.frame = window.contentView!.bounds
        hostingView.autoresizingMask = [.width, .height]
        window.contentView = hostingView
        
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
    
    func requestAccessibilityPermissions() {
        let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true]
        let accessEnabled = AXIsProcessTrustedWithOptions(options as CFDictionary)
        
        if !accessEnabled {
            let alert = NSAlert()
            alert.messageText = "Permissão de Acessibilidade Necessária"
            alert.informativeText = "Este app precisa de permissão de acessibilidade para gerenciar os Spaces. Por favor, ative nas Preferências do Sistema > Segurança e Privacidade > Acessibilidade."
            alert.alertStyle = .informational
            alert.addButton(withTitle: "Abrir Preferências")
            alert.addButton(withTitle: "Cancelar")
            
            if alert.runModal() == .alertFirstButtonReturn {
                NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")!)
            }
        }
    }
    
    func startMonitoring() {
        // Monitorar mudanças de spaces
        DistributedNotificationCenter.default().addObserver(
            self,
            selector: #selector(spaceChanged),
            name: NSNotification.Name("com.apple.spaces.switch"),
            object: nil
        )
        
        updateOverlays()
    }
    
    @objc func spaceChanged() {
        updateOverlays()
    }
    
    func updateOverlays() {
        // Remover overlays antigos
        overlayWindows.forEach { $0.close() }
        overlayWindows.removeAll()
        
        // Criar overlays para cada space
        if let spaces = spacesManager?.getAllSpaces() {
            for (index, space) in spaces.enumerated() {
                createOverlay(for: space, index: index)
            }
        }
    }
    
    func createOverlay(for space: SpaceInfo, index: Int) {
        let overlay = SpaceOverlayView(space: space, index: index)
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 200, height: 60),
            styleMask: [.borderless],
            backing: .buffered,
            defer: false
        )
        
        window.contentView = overlay
        window.backgroundColor = .clear
        window.isOpaque = false
        window.level = .floating
        window.ignoresMouseEvents = true
        window.collectionBehavior = [.canJoinAllSpaces, .stationary]
        
        // Posicionar no canto superior direito
        if let screen = NSScreen.main {
            let screenRect = screen.frame
            window.setFrameOrigin(NSPoint(
                x: screenRect.maxX - 220,
                y: screenRect.maxY - 80
            ))
        }
        
        window.makeKeyAndOrderFront(nil)
        overlayWindows.append(window)
    }
    
    func applicationWillTerminate(_ aNotification: Notification) {
        overlayWindows.forEach { $0.close() }
    }
    
    func applicationSupportsSecureRestorableState(_ app: NSApplication) -> Bool {
        return true
    }
}

extension AppDelegate: SpacesManagerDelegate {
    func spacesDidChange() {
        updateOverlays()
    }
}

