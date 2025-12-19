# Como Instalar e Compilar Spaces Renamer

## Pré-requisitos

- macOS 13.0 (Ventura) ou superior
- Xcode 14.0 ou superior
- Swift 5.7 ou superior

## Opção 1: Compilar no Xcode (Recomendado)

1. **Abra o Terminal e navegue até a pasta do projeto:**
```bash
cd /home/ubuntu/dumont-cloud/spaces-renamer
```

2. **Crie um novo projeto Xcode:**
   - Abra o Xcode
   - File > New > Project
   - Escolha "macOS" > "App"
   - Nome: "SpacesRenamer"
   - Language: Swift
   - Interface: SwiftUI (ou AppKit, ambos funcionam)
   - Salve o projeto

3. **Copie os arquivos para o projeto:**
   - Copie todos os arquivos `.swift` da pasta `SpacesRenamer/` para o projeto Xcode
   - Adicione ao target "SpacesRenamer"

4. **Configure o Info.plist:**
   - Adicione as configurações necessárias (já incluídas no Info.plist fornecido)

5. **Compile e execute:**
   - Pressione Cmd+B para compilar
   - Pressione Cmd+R para executar

## Opção 2: Compilar via Terminal (Swift Package Manager)

Se preferir usar Swift Package Manager:

1. **Crie um Package.swift:**
```bash
cd /home/ubuntu/dumont-cloud/spaces-renamer
swift package init --type executable
```

2. **Ajuste o Package.swift para incluir as dependências necessárias**

3. **Compile:**
```bash
swift build
```

## Configuração Pós-Instalação

1. **Permissões de Acessibilidade:**
   - O app solicitará permissão na primeira execução
   - Ou vá em: Preferências do Sistema > Segurança e Privacidade > Acessibilidade
   - Adicione "SpacesRenamer" à lista

2. **Permissões de Tela (se necessário):**
   - Para exibir overlays, pode ser necessário permitir "Gravação de Tela"

## Estrutura de Arquivos

```
spaces-renamer/
├── SpacesRenamer/
│   ├── AppDelegate.swift
│   ├── SpacesManager.swift
│   ├── SpaceOverlayView.swift
│   ├── ContentView.swift
│   └── Info.plist
├── README.md
└── INSTALL.md
```

## Notas Importantes

- O app funciona como um menu bar app (ícone na barra de menu)
- Os overlays aparecem no canto superior direito de cada Space
- Os nomes são salvos automaticamente em UserDefaults
- Cada Space tem uma cor diferente automaticamente

## Troubleshooting

**Problema:** Overlays não aparecem
- Verifique permissões de Acessibilidade
- Verifique permissões de Gravação de Tela
- Reinicie o app após conceder permissões

**Problema:** Não consigo renomear Spaces
- O app exibe overlays, mas não renomeia os Spaces nativamente do macOS
- Isso é uma limitação do macOS - não há API pública para renomear Spaces
- O overlay mostra o nome que você definiu

**Problema:** App não compila
- Verifique se está usando Xcode 14+ e macOS 13+
- Certifique-se de que todos os arquivos estão no target correto
- Verifique se está importando SwiftUI e AppKit corretamente

