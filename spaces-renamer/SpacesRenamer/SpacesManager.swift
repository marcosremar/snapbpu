import Cocoa
import AppKit

protocol SpacesManagerDelegate: AnyObject {
    func spacesDidChange()
}

struct SpaceInfo {
    let id: Int
    var name: String?
    let color: NSColor
}

class SpacesManager: ObservableObject {
    weak var delegate: SpacesManagerDelegate?
    private var spaces: [SpaceInfo] = []
    private let userDefaults = UserDefaults.standard
    private let spacesKey = "com.dumontcloud.spacesrenamer.spaces"
    
    // Cores pré-definidas para cada space
    private let spaceColors: [NSColor] = [
        .systemBlue,
        .systemGreen,
        .systemOrange,
        .systemPurple,
        .systemPink,
        .systemRed,
        .systemYellow,
        .systemTeal,
        .systemIndigo,
        .systemBrown
    ]
    
    init() {
        loadSpaces()
        setupNotifications()
    }
    
    private func setupNotifications() {
        // Observar mudanças de spaces
        NSWorkspace.shared.notificationCenter.addObserver(
            self,
            selector: #selector(activeSpaceChanged),
            name: NSWorkspace.activeSpaceDidChangeNotification,
            object: nil
        )
    }
    
    @objc private func activeSpaceChanged() {
        delegate?.spacesDidChange()
    }
    
    func getAllSpaces() -> [SpaceInfo] {
        // Obter número de spaces ativos
        let spaceCount = getSpaceCount()
        
        // Garantir que temos informações para todos os spaces
        while spaces.count < spaceCount {
            let newIndex = spaces.count
            let color = spaceColors[newIndex % spaceColors.count]
            let space = SpaceInfo(id: newIndex, name: nil, color: color)
            spaces.append(space)
        }
        
        // Carregar nomes salvos
        loadSavedNames()
        
        return spaces
    }
    
    func getSpaceCount() -> Int {
        // Tentar obter número de spaces via CGSSpace
        // Nota: Esta é uma API privada, mas é a forma mais confiável
        var count = 1
        
        // Método alternativo: usar NSScreen.spaces (se disponível)
        if let screens = NSScreen.screens {
            // Cada screen pode ter múltiplos spaces
            // Por enquanto, assumimos pelo menos 1 space por screen
            count = max(count, screens.count)
        }
        
        // Se tivermos nomes salvos, usar esse número como mínimo
        if let savedSpaces = userDefaults.array(forKey: spacesKey) as? [[String: Any]] {
            count = max(count, savedSpaces.count)
        }
        
        return max(count, spaces.count)
    }
    
    func setName(_ name: String?, forSpaceIndex index: Int) {
        guard index >= 0 && index < spaces.count else {
            // Expandir array se necessário
            while spaces.count <= index {
                let newIndex = spaces.count
                let color = spaceColors[newIndex % spaceColors.count]
                spaces.append(SpaceInfo(id: newIndex, name: nil, color: color))
            }
        }
        
        spaces[index] = SpaceInfo(
            id: spaces[index].id,
            name: name,
            color: spaces[index].color
        )
        
        saveSpaces()
        delegate?.spacesDidChange()
    }
    
    func getName(forSpaceIndex index: Int) -> String? {
        guard index >= 0 && index < spaces.count else { return nil }
        return spaces[index].name
    }
    
    func getColor(forSpaceIndex index: Int) -> NSColor {
        guard index >= 0 && index < spaces.count else {
            return spaceColors[index % spaceColors.count]
        }
        return spaces[index].color
    }
    
    private func loadSpaces() {
        // Inicializar com cores padrão
        for i in 0..<10 { // Máximo de 10 spaces
            let color = spaceColors[i % spaceColors.count]
            spaces.append(SpaceInfo(id: i, name: nil, color: color))
        }
        
        loadSavedNames()
    }
    
    private func loadSavedNames() {
        guard let savedSpaces = userDefaults.array(forKey: spacesKey) as? [[String: Any]] else {
            return
        }
        
        for (index, saved) in savedSpaces.enumerated() {
            if index < spaces.count {
                let name = saved["name"] as? String
                spaces[index] = SpaceInfo(
                    id: spaces[index].id,
                    name: name,
                    color: spaces[index].color
                )
            }
        }
    }
    
    private func saveSpaces() {
        let spacesData = spaces.map { space in
            [
                "id": space.id,
                "name": space.name ?? NSNull()
            ]
        }
        userDefaults.set(spacesData, forKey: spacesKey)
    }
}

