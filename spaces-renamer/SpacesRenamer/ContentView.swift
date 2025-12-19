import SwiftUI

struct PreferencesView: View {
    @ObservedObject var spacesManager: SpacesManager
    @State private var spaceNames: [String] = Array(repeating: "", count: 10)
    
    var body: some View {
        VStack(spacing: 20) {
            Text("Gerenciar Spaces")
                .font(.title)
                .fontWeight(.bold)
                .padding()
            
            ScrollView {
                VStack(spacing: 16) {
                    ForEach(0..<10, id: \.self) { index in
                        SpaceNameRow(
                            index: index,
                            name: Binding(
                                get: { spaceNames[index] },
                                set: { newValue in
                                    spaceNames[index] = newValue
                                    spacesManager.setName(newValue.isEmpty ? nil : newValue, forSpaceIndex: index)
                                }
                            ),
                            color: spacesManager.getColor(forSpaceIndex: index)
                        )
                    }
                }
                .padding()
            }
            
            HStack {
                Button("Salvar") {
                    // Nomes já são salvos automaticamente via binding
                    NSApp.keyWindow?.close()
                }
                .buttonStyle(.borderedProminent)
                
                Button("Cancelar") {
                    NSApp.keyWindow?.close()
                }
                .buttonStyle(.bordered)
            }
            .padding()
            
            Text("Digite um nome para cada Space. Se deixar vazio, será exibido apenas o número.")
                .font(.caption)
                .foregroundColor(.secondary)
                .padding(.horizontal)
        }
        .frame(width: 500, height: 600)
        .onAppear {
            loadSavedNames()
        }
    }
    
    private func loadSavedNames() {
        for i in 0..<10 {
            if let name = spacesManager.getName(forSpaceIndex: i) {
                spaceNames[i] = name
            }
        }
    }
}

struct SpaceNameRow: View {
    let index: Int
    @Binding var name: String
    let color: NSColor
    
    var body: some View {
        HStack(spacing: 12) {
            // Indicador de cor
            Circle()
                .fill(Color(nsColor: color))
                .frame(width: 24, height: 24)
            
            // Número do space
            Text("#\(index + 1)")
                .font(.system(.body, design: .monospaced))
                .foregroundColor(.secondary)
                .frame(width: 40, alignment: .leading)
            
            // Campo de texto
            TextField("Nome do Space \(index + 1)", text: $name)
                .textFieldStyle(.roundedBorder)
        }
        .padding(.horizontal)
    }
}
