import Cocoa

class PreferencesWindowController: NSWindowController {
    @IBOutlet weak var spaceNameFields: NSTableView!
    private var spacesManager: SpacesManager?
    private var spaceNames: [String] = Array(repeating: "", count: 10)
    
    override func windowDidLoad() {
        super.windowDidLoad()
        
        spacesManager = SpacesManager()
        loadSavedNames()
        
        // Configurar tabela
        spaceNameFields.delegate = self
        spaceNameFields.dataSource = self
        spaceNameFields.reloadData()
    }
    
    private func loadSavedNames() {
        guard let manager = spacesManager else { return }
        for i in 0..<10 {
            spaceNames[i] = manager.getName(forSpaceIndex: i) ?? ""
        }
    }
    
    @IBAction func saveButtonClicked(_ sender: Any) {
        guard let manager = spacesManager else { return }
        for (index, name) in spaceNames.enumerated() {
            manager.setName(name.isEmpty ? nil : name, forSpaceIndex: index)
        }
        window?.close()
    }
}

extension PreferencesWindowController: NSTableViewDataSource, NSTableViewDelegate {
    func numberOfRows(in tableView: NSTableView) -> Int {
        return 10
    }
    
    func tableView(_ tableView: NSTableView, viewFor tableColumn: NSTableColumn?, row: Int) -> NSView? {
        guard let column = tableColumn else { return nil }
        
        let identifier = column.identifier
        let cellView = tableView.makeView(withIdentifier: identifier, owner: self) as? NSTableCellView
        
        if identifier.rawValue == "ColorColumn" {
            // Coluna de cor
            let color = spacesManager?.getColor(forSpaceIndex: row) ?? .systemBlue
            cellView?.imageView?.image = createColorCircle(color: color)
            cellView?.textField?.stringValue = "#\(row + 1)"
        } else if identifier.rawValue == "NameColumn" {
            // Coluna de nome
            let textField = NSTextField(frame: NSRect(x: 0, y: 0, width: 200, height: 22))
            textField.stringValue = spaceNames[row]
            textField.placeholderString = "Nome do Space \(row + 1)"
            textField.tag = row
            textField.target = self
            textField.action = #selector(nameFieldChanged(_:))
            return textField
        }
        
        return cellView
    }
    
    @objc func nameFieldChanged(_ sender: NSTextField) {
        let index = sender.tag
        if index >= 0 && index < spaceNames.count {
            spaceNames[index] = sender.stringValue
        }
    }
    
    private func createColorCircle(color: NSColor) -> NSImage {
        let size = NSSize(width: 20, height: 20)
        let image = NSImage(size: size)
        image.lockFocus()
        color.setFill()
        NSBezierPath(ovalIn: NSRect(origin: .zero, size: size)).fill()
        image.unlockFocus()
        return image
    }
}

