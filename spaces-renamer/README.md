# Spaces Renamer

Aplicação macOS para gerenciar e exibir nomes personalizados nos Spaces do macOS.

## Funcionalidades

- ✅ Adicionar nomes personalizados para cada Space
- ✅ Exibir overlay com nome e número do Space
- ✅ Cada Space tem uma cor diferente
- ✅ Se não tiver nome, mostra apenas o número
- ✅ Interface na barra de menu para gerenciar

## Requisitos

- macOS 13.0 ou superior
- Xcode 14.0 ou superior
- Permissão de Acessibilidade (necessária para gerenciar Spaces)

## Como Compilar

1. Abra o projeto no Xcode:
```bash
open SpacesRenamer.xcodeproj
```

2. Selecione o target "SpacesRenamer"

3. Pressione Cmd+B para compilar

4. Execute o app (Cmd+R)

## Como Usar

1. Ao abrir o app pela primeira vez, ele solicitará permissão de acessibilidade
2. Clique no ícone na barra de menu
3. Selecione "Gerenciar Spaces"
4. Digite um nome para cada Space desejado
5. O overlay aparecerá no canto superior direito de cada Space

## Permissões Necessárias

O app precisa de permissão de **Acessibilidade** para:
- Detectar mudanças de Spaces
- Exibir overlays em todos os Spaces
- Gerenciar nomes dos Spaces

Para ativar:
1. Preferências do Sistema > Segurança e Privacidade > Acessibilidade
2. Adicione "SpacesRenamer" à lista

## Estrutura do Projeto

```
SpacesRenamer/
├── AppDelegate.swift          # Gerenciamento principal do app
├── SpacesManager.swift        # Lógica de gerenciamento de Spaces
├── SpaceOverlayView.swift     # View do overlay exibido
├── ContentView.swift          # Interface de gerenciamento (SwiftUI)
└── Info.plist                # Configurações do app
```

## Notas Técnicas

- Usa `NSWorkspace` para detectar mudanças de Spaces
- Overlays são criados como janelas flutuantes (`NSWindow` com `.floating`)
- Nomes são salvos em `UserDefaults`
- Cores são pré-definidas e rotacionam para cada Space

## Limitações

- O macOS não fornece uma API pública oficial para renomear Spaces
- Esta implementação exibe overlays, mas não renomeia os Spaces nativamente
- Pode ser necessário ajustar posicionamento do overlay dependendo da resolução

## Melhorias Futuras

- [ ] Permitir personalizar cores
- [ ] Posicionamento customizável do overlay
- [ ] Suporte a ícones personalizados
- [ ] Atalhos de teclado para renomear rapidamente

