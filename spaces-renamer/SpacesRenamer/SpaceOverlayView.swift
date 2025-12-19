import Cocoa
import AppKit

class SpaceOverlayView: NSView {
    private let space: SpaceInfo
    private let index: Int
    
    init(space: SpaceInfo, index: Int) {
        self.space = space
        self.index = index
        super.init(frame: NSRect(x: 0, y: 0, width: 200, height: 60))
        setupView()
    }
    
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    private func setupView() {
        wantsLayer = true
        layer?.cornerRadius = 12
        layer?.backgroundColor = space.color.withAlphaComponent(0.2).cgColor
        layer?.borderWidth = 2
        layer?.borderColor = space.color.cgColor
    }
    
    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)
        
        // Desenhar fundo
        let backgroundPath = NSBezierPath(roundedRect: bounds, xRadius: 12, yRadius: 12)
        space.color.withAlphaComponent(0.15).setFill()
        backgroundPath.fill()
        
        // Desenhar borda
        space.color.setStroke()
        backgroundPath.lineWidth = 2
        backgroundPath.stroke()
        
        // Desenhar ícone
        let iconSize: CGFloat = 24
        let iconRect = NSRect(
            x: 12,
            y: (bounds.height - iconSize) / 2,
            width: iconSize,
            height: iconSize
        )
        
        if let icon = NSImage(systemSymbolName: "square.grid.2x2", accessibilityDescription: nil) {
            icon.lockFocus()
            space.color.set()
            let iconPath = NSRect(origin: .zero, size: icon.size)
            iconPath.fill(using: .sourceAtop)
            icon.unlockFocus()
            icon.draw(in: iconRect)
        }
        
        // Desenhar texto
        let textRect = NSRect(
            x: iconRect.maxX + 8,
            y: 0,
            width: bounds.width - iconRect.maxX - 16,
            height: bounds.height
        )
        
        // Nome do space ou número
        let displayText: String
        if let name = space.name, !name.isEmpty {
            displayText = "\(name)\n#\(index + 1)"
        } else {
            displayText = "Space #\(index + 1)"
        }
        
        let paragraphStyle = NSMutableParagraphStyle()
        paragraphStyle.alignment = .left
        paragraphStyle.lineSpacing = 2
        
        let attributes: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 13, weight: .semibold),
            .foregroundColor: NSColor.labelColor,
            .paragraphStyle: paragraphStyle
        ]
        
        displayText.draw(in: textRect, withAttributes: attributes)
    }
}

