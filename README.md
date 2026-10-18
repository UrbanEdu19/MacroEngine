# 🚀 MacroEngine - Desktop Server

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Plataforma-Windows%2010%20%2F%2011%20%7C%20Linux-0078D6.svg?style=for-the-badge&logo=windows&logoColor=white)
![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI-2B5B84.svg?style=for-the-badge)
![License](https://img.shields.io/badge/Licen%C3%A7a-MIT-green.svg?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Produ%C3%A7%C3%A3o%20Est%C3%A1vel-brightgreen.svg?style=for-the-badge)

<p align="center">
  <b>Servidor desktop de automação de ultra-baixa latência, controle remoto completo, espelhamento de tela bidirecional a 60 FPS, streaming de áudio sem fio via UDP e mais de 100 macros otimizadas para os jogos mais jogados do mundo (Counter-Strike 2, Deadlock, COD Warzone, Helldivers 2, PUBG, Apex Legends, Valorant, Delta Force, Battlefield 6) e produtividade.</b>
</p>

[Visão Geral](#-visão-geral) •
[Arquitetura](#-arquitetura-do-sistema) •
[Recursos](#-recursos-principais) •
[Instalação Rápida](#-instalação-rápida-em-1-clique) •
[Iniciar com o Windows](#-inicialização-automática-com-o-windows) •
[Endpoints da API](#-documentação-da-api-rest) •
[Macros](#-tabela-de-macros-embutidas) •
[Diagnóstico](#-diagnóstico-e-testes) •
[Apoie o Projeto](#-apoie-o-projeto--contribuição)
</div>

---

## 📖 Visão Geral

O **MacroEngine Desktop Server** é a espinha dorsal do ecossistema MacroEngine. Construído em Python com **FastAPI** e **Uvicorn**, ele expõe uma API RESTful de alta performance que permite ao aplicativo mobile (Android) ou a qualquer cliente de rede:

1. **Controlar o PC remotamente**: Movimentação e cliques de mouse, atalhos de teclado, controle de janelas, mídia e comandos do sistema operacional.
2. **Espelhamento de Tela Bidirecional**:
   - Tela do PC no Celular: Captura acelerada por hardware (DirectX/MSS) a até 60 FPS com comandos de clique e toque na tela.
   - Tela do Celular no PC: Integração nativa com **Scrcpy** e **ADB** para espelhamento em tela cheia com latência inferior a 15ms.
3. **Transmissão de Áudio sem Fio (UDP PCM)**: Ouça o áudio do computador diretamente nos fones do smartphone em tempo real.
4. **Inicialização Silenciosa com o Windows (Auto-Start)**: O servidor pode ser configurado para iniciar automaticamente em segundo plano ao ligar o computador, sem exibir janelas pretas de prompt ou CMD.
5. **Ícone na Bandeja do Sistema (System Tray)**: Acesso rápido a status em tempo real, documentação Swagger, alternador de Modo Jogo Turbo e controle de autostart diretamente pela bandeja do Windows.
6. **Modo Jogo Turbo & Mais de 100 Macros**: Comandos táticos para os jogos mais jogados do momento (CS2, Deadlock, Warzone, Helldivers 2, PUBG, Apex, Valorant, Delta Force, Battlefield), controle de clipes Nvidia ShadowPlay, OBS Studio, Discord, além de macros de produtividade e controle do próprio celular via ADB.

> 📱 **Aplicativo Android Pronto para Instalação:** O instalador **`MacroEngine-1.1.8v.apk`** já está incluso diretamente na raiz deste repositório! Basta passá-lo para o seu celular Android e instalar diretamente, sem precisar de Android Studio ou compilação.

---

## 🏗 Arquitetura do Sistema

```mermaid
flowchart TD
    subgraph Mobile ["📱 Smartphone Android (Remote Master App)"]
        UI["Interface Gráfica (Flutter/Jetpack Compose)"]
        AudioRecv["Player de Áudio UDP (Porta 50005)"]
        HTTPClient["Cliente HTTP REST (Porta 8000)"]
    end

    subgraph Server ["💻 Desktop Server (FastAPI + AsyncIO)"]
        Router["FastAPI Router (/api)"]
        Tray["System Tray (pystray)"]
        ConfigManager["Config Manager (config.json)"]
        ScreenWorker["Capturador de Tela DirectX (MSS/GDI)"]
        AudioWorker["Audio Streamer UDP (PyAudio/PCM)"]
        MacroEngine["Engine de Macros (PyAutoGUI + OS)"]
        ScrcpyBridge["Scrcpy / ADB Bridge"]
    end

    subgraph OS ["🪟 Windows OS & Hardware"]
        WinRegistry["Registro (HKCU Run Autostart)"]
        PowerCfg["Plano de Energia Turbo (powercfg)"]
        WinAudio["Áudio Master (pycaw CoreAudio)"]
        Display["Monitores & GPU (Desktop winsta0)"]
        NIC["Placa de Rede Física (Wake-on-LAN)"]
    end

    UI -->|Comandos REST| HTTPClient
    HTTPClient -->|TCP 8000| Router
    AudioWorker -.->|UDP 50005 (PCM 44.1kHz)| AudioRecv
    ScreenWorker -->|Frames JPEG / Stream| UI

    Router --> MacroEngine
    Router --> ScreenWorker
    Router --> AudioWorker
    Router --> ScrcpyBridge
    Router --> ConfigManager

    Tray -->|Status & Controle| ConfigManager
    MacroEngine -->|Controle de Teclas/Mouse| Display
    MacroEngine -->|Plano de Alto Desempenho| PowerCfg
    MacroEngine -->|Silêncio Absoluto| WinAudio
    ConfigManager -->|Auto-Start| WinRegistry
    Router -->|Diagnóstico MAC| NIC
```

---

## ✨ Recursos Principais

### 1. 🚀 Inicialização com o Windows 100% Silenciosa (Auto-Start)
- O servidor pode ser configurado para inicializar com o Windows em modo invisível através do script `run_silent.vbs` acoplado ao Registro do Windows (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`).
- Nenhuma janela preta de console (CMD) fica aberta. O servidor roda limpo em segundo plano e exibe um ícone discreto na bandeja do sistema ao lado do relógio.

### 2. 💻 Menu da Bandeja do Sistema (System Tray)
- Ícone dinâmico em alta definição gerado via Pillow.
- Ponto luminoso verde indicando status **Online**.
- **Menu interativo ao clicar com o botão direito**:
  - `⚡ MacroEngine (Porta 8000)`
  - `🌐 Abrir Documentação (Swagger Docs)`
  - `🎮 Modo Jogo Turbo` (com indicador visual de ligado/desligado)
  - `🚀 Iniciar com o Windows` (permite ligar ou desligar o autostart com 1 clique)
  - `🛑 Encerrar Servidor`

### 3. 🎮 Modo Jogo Turbo & Macros Táticas
- **Modo Jogo Turbo**: Alterna dinamicamente o plano de energia do Windows para **Alto Desempenho Máximo** (`powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c`), liberando frequências de clock máximas na CPU e GPU.
- **Macros Especiais para Battlefield & FPS**:
  - `bf_spotting`: Rajada de marcação tática de alvos (Q-Spotting contínuo).
  - `bf_hold_breath`: Estabilização de mira sniper automática (Shift sustentado por 2.5s).
  - `bf_medkit_ammo`: Descarte instantâneo de caixas de munição e kit médico para o esquadrão.
  - `bf_drop_shot`: Drop-shot defensivo rápido para desviar de disparos.
  - `instant_replay`: Salva clipes instantâneos no Nvidia ShadowPlay (`Alt+F10`).
  - `game_clip`: Salva os últimos 30 segundos de gameplay via Xbox Game Bar (`Win+Alt+G`).
  - `obs_record` e `obs_stream`: Inicia ou pausa gravações e lives no OBS Studio.
  - `discord_mute` e `discord_deafen`: Muta microfone e áudio do Discord à distância.

### 4. 📱 Espelhamento de Tela Bidirecional
- **PC no Celular**: Endpoint `/api/screen/frame` (captura otimizada por MSS em menos de 10ms) e `/api/screen/stream` (Multipart MJPEG contínuo).
- **Celular no PC**: Endpoint `/api/mirror/start` dispara o **Scrcpy** em 60 FPS com taxa de 12 Mbps e controle total de mouse e teclado.

### 5. 🔊 Áudio Master & Transmissão sem Fio
- Streaming de pacotes PCM brutos de 16-bit estéreo a 44.1 kHz via soquetes UDP para latência praticamente imperceptível.
- **Controle de Volume no Hardware (CoreAudio Windows)**: Ajuste granular de volume (`vol_up`, `vol_down`, `vol_boost_up`, `vol_boost_down`) e mudo operando diretamente no nível do driver de som via `EndpointVolume` do Windows, sem depender de janelas ativas ou foco do teclado.
- **Botão de Pânico / Mudo Inteligente com Alternância (Toggle)**: Endpoint `/api/mute` e macro `vol_mute` alternam o som de forma bidirecional — se o PC estiver com som, ele muta e pausa as mídias; se já estiver mutado, um segundo toque desmuta e restaura o som do computador imediatamente.

### 6. ⚡ Wake-on-LAN (Ligar PC Remotamente)
- O servidor detecta automaticamente o endereço MAC da placa de rede física principal ativa (desconsiderando adaptadores virtuais de WSL, Hyper-V e VPNs) através do endpoint `/api/wol/info`.

### 7. 📁 Transferência Ultrarrápida de Arquivos (PC ⇄ Celular)
- **Celular para o PC**: Selecione qualquer arquivo (fotos, vídeos, documentos, compactados ZIP) no smartphone e envie diretamente para o computador. O arquivo é salvo na pasta `server/shared_files/` e o caminho completo no Windows é retornado com confirmação.
- **PC para o Celular**: Todos os arquivos colocados na pasta `server/shared_files/` no computador ficam visíveis na hora no aplicativo. O usuário pode baixar rapidamente direto na pasta pública `Download/RemoteMasterPro/` do Android ou escolher manualmente qualquer pasta pelo seletor nativo do sistema ("Salvar Como...").
- **Abertura Remota da Pasta no Explorer**: Com 1 toque no app mobile (`/api/files/open-folder`), o servidor abre a pasta compartilhada no Explorador de Arquivos do Windows na tela do PC.

### 8. 🌐 Lançador de Links Inteligente & Painel Web do Celular
- **Painel do Celular Integrado ao Menu Principal**: O estado e acesso ao servidor web embarcado no smartphone (`http://localhost:8080` / `http://<ip-celular>:8080`) fica em destaque logo abaixo do Estado do Servidor no menu inicial, com botões para abrir no celular, enviar ao PC e copiar a URL.
- **Despacho Direto ao Navegador do PC (`/api/open-url`)**: Abre qualquer URL (YouTube, WhatsApp Web, ChatGPT, sites de compras) diretamente no navegador padrão configurado no Windows através do módulo nativo `webbrowser.open(url)` com fallback seguro via `os.startfile(url)`.
- **Atalhos Rápidos de 1 Toque**: Catálogo amplo de atalhos rápidos organizados por categorias (`Web`, `IA`, `Mídia`, `Compras`). Um toque no atalho despacha imediatamente o link para o computador, além de contar com o botão `[📱 Celular]` para abertura local e `[💻 PC]` para envio direcionado.

---

## 🛠 Instalação Rápida em 1 Clique

### Pré-requisitos:
- **Windows 10 ou 11** (64-bit)
- **Python 3.10 ou superior** instalado (marque a opção *"Add python.exe to PATH"* durante a instalação)

### Passo a Passo:

1. Clone ou baixe este repositório no seu computador:
   ```bash
   git clone https://github.com/UrbanEdu19/MacroEngine.git
   cd MacroEngine
   ```

2. **Execute o configurador automático de ambiente**:
   Dê dois cliques no arquivo:
   ```text
   setup_environment.bat
   ```
   *O instalador irá:*
   - Criar o ambiente virtual isolado `.venv`
   - Atualizar o `pip`
   - Instalar todas as dependências do `requirements.txt`
   - Oferecer a liberação automática das portas no Firewall do Windows
   - Oferecer a configuração da inicialização automática com o Windows

---

## 🚀 Como Executar o Servidor

Você tem três formas convenientes de executar o servidor:

### Opção 1: Modo Normal com Janela de Console (Para testes e depuração)
Dê dois cliques em:
```text
start_server.bat
```
*Abre o prompt de comando exibindo todos os logs da API, requisições HTTP e endereços IP locais.*

### Opção 2: Modo Silencioso em Segundo Plano (Background)
Dê dois cliques em:
```text
start_server_background.bat
```
*Inicia o servidor de forma 100% invisível através de `pythonw.exe`. O ícone do MacroEngine aparecerá na bandeja do sistema ao lado do relógio do Windows.*

### Opção 3: Inicialização Automática com o Windows (Auto-Start Permanente)
Para que o servidor sempre ligue sozinho quando você ligar ou reiniciar o PC:
1. Dê dois cliques em `install_autostart.bat`.
2. O script registra a inicialização silenciosa no Registro do Windows (`HKCU Run`).
3. Pronto! Ao ligar o computador, o servidor já estará ativo e aguardando comandos do seu celular.

> [!TIP]
> **Para desativar a inicialização automática**, basta dar dois cliques em `uninstall_autostart.bat` ou desmarcar a opção diretamente no menu do ícone da bandeja do sistema.

### Para Encerrar o Servidor Ativo:
- Dê dois cliques em `stop_server.bat` ou clique com o botão direito no ícone da bandeja e selecione **"Encerrar Servidor"**.

---

## 🛡 Configuração de Rede e Firewall

Para que o celular se conecte ao servidor pela rede Wi-Fi local sem bloqueios do Windows Defender:

1. Clique com o botão direito em `register_firewall.bat` e escolha **"Executar como Administrador"**.
2. O script liberará:
   - **Porta TCP 8000**: API REST e Streaming de Tela
   - **Porta UDP 50005**: Transmissão de Áudio sem Fio

---

## 🔌 Documentação da API REST

A documentação interativa completa (Swagger OpenAPI) fica disponível no navegador assim que o servidor estiver rodando:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Redoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Principais Endpoints:

| Método | Endpoint | Descrição |
| :--- | :--- | :--- |
| `GET` | `/api/status` | Retorna o status operacional, IP local, MAC, autostart e status do Modo Jogo |
| `GET` | `/api/config` | Retorna as configurações atuais do arquivo `config.json` |
| `GET` | `/api/wol/info` | Retorna o MAC físico principal e portas recomendadas para Wake-on-LAN |
| `POST` | `/api/mute` | **Botão de Pânico**: Muta áudio master e pausa mídias |
| `POST` | `/api/game-mode/toggle` | Alterna o Modo Jogo Turbo (Alto Desempenho / Equilibrado) |
| `GET` | `/api/autostart/status` | Verifica se a inicialização com o Windows está habilitada |
| `POST` | `/api/autostart/enable` | Ativa a inicialização automática silenciosa no Registro do Windows |
| `POST` | `/api/autostart/disable`| Remove a inicialização automática do Windows |
| `POST` | `/api/autostart/toggle` | Alterna o estado da inicialização automática |
| `GET` | `/api/macros` | Lista todas as macros disponíveis com nomes e categorias |
| `POST` | `/api/macro/{id}` | Dispara a execução de uma macro no computador |
| `POST` | `/api/phone/macro/{id}`| Dispara comando/macro para o celular conectado via ADB |
| `POST` | `/api/phone/touch` | Simula toque normalizado na tela do celular via ADB |
| `GET` | `/api/screen/frame` | Captura e retorna o frame atual da tela do PC (JPEG otimizado) |
| `GET` | `/api/screen/stream` | Stream contínuo de vídeo da tela em formato MJPEG |
| `POST` | `/api/screen/input` | Injeta clique de mouse na tela do PC via coordenadas normalizadas |
| `POST` | `/api/mirror/start` | Abre o espelhamento Scrcpy da tela do celular no monitor do PC |
| `POST` | `/api/mirror/stop` | Encerra o espelhamento do Scrcpy |
| `GET` | `/api/mirror/status` | Retorna se o espelhamento Scrcpy está em execução |
| `POST` | `/api/audio/start` | Inicia o envio de áudio PCM UDP para o IP do smartphone |
| `POST` | `/api/audio/stop` | Interrompe o envio de áudio |
| `POST` | `/api/open-url` | Abre qualquer link/URL no navegador padrão do PC |
| `POST` | `/api/system/sleep` | Coloca o computador em suspensão profunda (Sleep S3 - Recomendado para Ignição) |
| `POST` | `/api/system/shutdown` | Desliga o computador completamente |
| `POST` | `/api/server/shutdown` | Encerra o processo do servidor desktop com segurança |
| `POST` | `/api/files/upload` | Envia arquivos do celular para a pasta compartilhada do PC |
| `GET` | `/api/files/list` | Lista arquivos presentes na pasta compartilhada do PC com tamanho e datas |
| `GET` | `/api/files/download/{filename}` | Baixa arquivo da pasta compartilhada do PC para o smartphone |
| `POST` | `/api/files/open-folder` | Abre a pasta compartilhada no Windows Explorer do computador |
| `DELETE` | `/api/files/delete/{filename}` | Exclui arquivo da pasta compartilhada do PC |

---

## 🎮 Tabela de Macros Embutidas

O servidor conta com mais de 150 macros prontas, organizadas por 20 categorias profissionais:

### 1. Battlefield 6 & Jogos FPS
- `bf_spotting`: Rajada rápida de Q para marcar inimigos no mapa.
- `bf_hold_breath`: Segura respiração da mira telescópica por 2.5s.
- `bf_medkit_ammo`: Solta caixa médica e caixa de munição instantaneamente.
- `bf_drop_shot`: Deita rapidamente em combate para esquivar.
- `bf_crouch_slide`: Agachar e deslizar tático.
- `bf_reload_cancel`: Cancelamento rápido de recarga.
- `bf_jump_shot`: Pulo com disparo.
- `bf_ping_danger`: Marcação de perigo/alerta vermelho.
- `bf_switch_sidearm`: Puxar arma secundária/pistola rapidamente.
- `bf_gadget1` / `bf_gadget2`: Acesso instantâneo a equipamentos táticos.
- `bf_melee`: Golpe de faca imediato.
- `bf_scoreboard`: Placar e mapa geral da partida.

### 2. Gaming, OBS & Gravação
- `game_mode_boost`: Liga o Modo Jogo Turbo (Plano de Alto Desempenho).
- `fps_overlay`: Exibe ou oculta contador de FPS (`Alt+R`).
- `instant_replay`: Salva clipe instantâneo no GeForce Experience (`Alt+F10`).
- `game_clip`: Grava os últimos 30 segundos no Xbox Game Bar (`Win+Alt+G`).
- `steam_overlay`: Abre o painel integrado da Steam (`Shift+Tab`).
- `open_steam`: Lança a aplicação Steam no desktop.
- `obs_record`: Dispara/para gravação no OBS Studio (`Ctrl+F9`).
- `obs_stream`: Inicia/para transmissão ao vivo no OBS Studio (`Ctrl+F10`).
- `discord_mute`: Alterna microfone mudo no Discord (`Ctrl+Shift+M`).
- `discord_deafen`: Ensordece/desensordece áudio do Discord (`Ctrl+Shift+D`).
- `voice_typing`: Ativa digitação por voz do Windows (`Win+H`).

### 3. Counter-Strike 2 (CS2)
- `cs2_drop_c4`: Seleciona bomba C4 (`5`), dropa para companheiro (`G`) e volta para arma principal (`1`).
- `cs2_jump_throw`: Pulo sincronizado com soltura de granada para smokes perfeitas.
- `cs2_inspect`: Inspecionar e girar faca/skin no estilo dos pro players (`F + R`).
- `cs2_quick_flash`: Puxa granada Flashbang instantaneamente (`7`).
- `cs2_drop_pistol`: Joga pistola secundária para teammate sem trocar da arma primária.
- `cs2_radar_zoom`: Alterna nível de zoom do minimapa radar.

### 4. Deadlock (Valve)
- `deadlock_dash_jump`: Combo sincronizado de Dash (`Shift`) e Pulo (`Espaço`) para aceleração extrema.
- `deadlock_heavy_melee`: Carrega e dispara soco corporal pesado concentrado.
- `deadlock_parry`: Aparo/Parry defensivo contra golpes corporais inimigos (`F`).
- `deadlock_shop`: Abre e fecha o menu da loja de melhorias táticas (`B`).
- `deadlock_ping_boss`: Ping tático de alerta no Mid Boss ou na Urna de Almas (`Mouse3`).

### 5. Call of Duty: Warzone & MW3
- `cod_slide_cancel`: Slide Cancel clássico de movimentação fluida (`Ctrl -> Ctrl -> Espaço`).
- `cod_plate_spam`: Aplica 3 placas de blindagem mantendo a tecla `4` pressionada.
- `cod_ping_danger`: Marcação dupla vermelha rápida de inimigo avistado (`Alt duplo`).
- `cod_drop_munitions`: Solta caixa de munições ou placas táticas (`5`).
- `cod_mount_weapon`: Apoia a arma em quinas ou janelas (`Z`).

### 6. Helldivers 2 (Estratagemas Automatizados)
- `hd2_reinforce`: Chama reforço para reviver o esquadrão (`⬆ ⬇ ➡ ⬅ ⬆`).
- `hd2_bomb_500kg`: Bomba Águia de 500kg devastadora (`⬆ ➡ ⬇ ⬇ ⬇`).
- `hd2_resupply`: Pede suprimentos de munição e stims (`⬇ ⬇ ⬆ ➡`).
- `hd2_orbital_laser`: Dispara o Laser Orbital destruidor de fortalezas (`➡ ⬇ ⬆ ➡ ⬇`).
- `hd2_railcannon`: Golpe de Canhão Elétrico Orbital anti-tanque (`➡ ⬆ ⬇ ⬇ ➡`).
- `hd2_stim_heal`: Cura rápida com injeção de Stim (`V`).

### 7. PUBG: BATTLEGROUNDS
- `pubg_crouch_jump`: Pulo agachado para saltar janelas sem quebrar o ritmo (`Espaço + C`).
- `pubg_boost_energy`: Consome Energético / Analgésico rapidamente (`8`).
- `pubg_first_aid`: Aplica Kit de Primeiros Socorros instantâneo (`7`).
- `pubg_driver_seat`: Muda diretamente para o assento de motorista do carro (`Ctrl+1`).
- `pubg_smoke_grenade`: Puxa granada de fumaça de emergência (`5`).

### 8. Apex Legends
- `apex_holster_run`: Guarda a arma no coldre (`3`) para velocidade máxima de corrida e reposicionamento.
- `apex_shield_battery`: Seleciona e usa Bateria de Escudo (`4`).
- `apex_phoenix_kit`: Consome Kit Fênix de restauração completa de vida e escudo.
- `apex_ping_enemy`: Marcação rápida de inimigo próximo (`F`).
- `apex_superglide`: Auxiliar com timing de pulo e agachamento para superglide.

### 9. Valorant
- `val_spike_plant`: Segura a tecla `4` pelo tempo necessário para plantar ou defusar a Spike.
- `val_knife_run`: Puxa faca rápida para rotação veloz pelo mapa (`3`).
- `val_ping_danger`: Alerta sonoro e visual de perigo para a equipe (`Z`).
- `val_drop_weapon`: Joga arma no chão para compra de companheiro (`G`).

### 10. Delta Force & ARC Raiders
- `delta_tactical_heal`: Bandagem rápida e estancamento de sangramento (`4`).
- `delta_armor_plate`: Reparo de colete e placa de proteção (`5`).
- `delta_canted_sight`: Alterna mira inclinada / scope híbrido (`V`).
- `delta_special_gadget`: Dispara gadget ou drone tático da classe (`X`).

### 11. Rust (Sobrevivência)
- `rust_auto_gather`: Coleta contínua de madeira/minérios automática por 6 segundos.
- `rust_suicide_f1`: Abre console `F1` e executa respawn (`kill`) instantâneo para voltar à base.
- `rust_craft_bandage`: Atalho para criar curativos no inventário (`Tab`).

### 12. Fortnite
- `fortnite_wall_ramp`: Constrói Parede + Rampa defensiva em rápida sucessão (`F1 + F3`).
- `fortnite_shield_potion`: Consome Poção de Escudo / Mini Shield (`Slot 5`).
- `fortnite_ping_enemy`: Marcação tática de alvo inimigo no mapa.

### 13. Gerenciamento de Janelas & Telas
- `win_d`: Minimiza tudo e mostra o Desktop.
- `alt_tab`: Alterna entre aplicativos abertos.
- `snap_left` / `snap_right`: Encaixa a janela ativa na metade esquerda ou direita.
- `maximize_window`: Maximiza a janela ativa (`Win+Up`).
- `minimize_window`: Minimiza a janela atual.
- `fullscreen_f11`: Alterna modo tela cheia (`F11`).
- `next_monitor`: Move a janela diretamente para o próximo monitor (`Win+Shift+Right`).
- `close_window`: Fecha a janela ativa (`Alt+F4`).

### 14. Mídia & Volume
- `play_pause`: Toca ou pausa a reprodução de mídia global.
- `next_track` / `prev_track`: Próxima faixa ou faixa anterior.
- `vol_up_5` / `vol_down_5`: Aumenta ou diminui 5 passos do volume master.
- `skip_fwd_10s` / `skip_back_10s`: Avança ou retrocede 10 segundos em reprodutores de vídeo.
- `toggle_fullscreen`: Alterna tela cheia no player de vídeo (`F`).

### 15. Produtividade & Navegação
- `clipboard_history`: Abre o histórico da área de transferência do Windows (`Win+V`).
- `search_pc`: Busca global no Windows (`Win+S`).
- `close_tab`: Fecha a aba ativa do navegador (`Ctrl+W`).
- `reopen_tab`: Restaura a última aba fechada (`Ctrl+Shift+T`).
- `incognito_tab`: Abre janela anônima privada (`Ctrl+Shift+N`).
- `save_all`: Salva arquivos em editores (`Ctrl+S`).
- `screenshot`: Ferramenta de captura de tela do Windows (`Win+Shift+S`).
- `open_notepad`: Abre o Bloco de Notas.
- `open_calc`: Abre a Calculadora do Windows.
- `file_explorer`: Abre o Explorador de Arquivos (`Win+E`).
- `open_terminal`: Abre o Terminal PowerShell.

### 16. Microsoft Word & LibreOffice Writer (Documentos)
- `office_bold`: Formatar texto selecionado em Negrito (`Ctrl+B`).
- `office_italic`: Formatar texto selecionado em Itálico (`Ctrl+I`).
- `office_underline`: Sublinhar texto selecionado (`Ctrl+U`).
- `office_align_center`: Centralizar parágrafo (`Ctrl+E`).
- `office_align_left` / `office_align_right`: Alinhar à esquerda (`Ctrl+L`) ou direita (`Ctrl+R`).
- `office_align_justify`: Justificar texto (`Ctrl+J`).
- `office_save_doc`: Salvar documento ativo (`Ctrl+S`).
- `office_find_replace`: Abrir janela de Localizar e Substituir (`Ctrl+H`).
- `office_page_break`: Inserir quebra de página instantânea (`Ctrl+Enter`).
- `office_insert_link`: Inserir hiperlink no texto selecionado (`Ctrl+K`).
- `office_select_all`: Selecionar todo o conteúdo do documento (`Ctrl+A`).
- `office_print_pdf`: Abrir diálogo de Impressão / Exportar para PDF (`Ctrl+P`).

### 17. Microsoft Excel & LibreOffice Calc (Planilhas & Dados)
- `excel_auto_sum`: Inserir AutoSoma automática da coluna ou linha (`Alt+=`).
- `excel_insert_row`: Inserir nova linha ou célula na planilha (`Ctrl+Shift+=`).
- `excel_delete_row`: Excluir linha ou célula selecionada (`Ctrl+-`).
- `excel_format_currency`: Formatar valores numéricos como Moeda R$ (`Ctrl+Shift+4`).
- `excel_format_percent`: Formatar como Porcentagem % (`Ctrl+Shift+5`).
- `excel_format_date`: Formatar células no padrão Data (`Ctrl+Shift+3`).
- `excel_filter_toggle`: Ativar ou desativar filtros de dados (`Ctrl+Shift+L`).
- `excel_new_sheet`: Inserir nova planilha no documento (`Shift+F11`).
- `excel_create_chart`: Criar gráfico instantâneo dos dados selecionados (`F11`).
- `excel_flash_fill`: Executar Preenchimento Relâmpago / Inteligente (`Ctrl+E`).
- `excel_edit_cell`: Entrar no modo de edição da célula ativa (`F2`).

### 18. PowerPoint & LibreOffice Impress (Apresentações de Slides)
- `ppt_start_slideshow`: Iniciar apresentação de slides a partir do início (`F5`).
- `ppt_present_current`: Apresentar a partir do slide atual (`Shift+F5`).
- `ppt_next_slide` / `ppt_prev_slide`: Avançar (`PageDown`) ou retroceder (`PageUp`) slide.
- `ppt_new_slide`: Inserir novo slide na apresentação (`Ctrl+M`).
- `ppt_duplicate_slide`: Duplicar slide selecionado (`Ctrl+D`).
- `ppt_laser_pointer`: Ativar ponteiro laser virtual durante a apresentação (`Ctrl+L`).
- `ppt_pen_tool`: Ativar ferramenta de caneta para desenhar na tela (`Ctrl+P`).
- `ppt_black_screen`: Apagar a projeção / alternar tela preta (`B`).
- `ppt_white_screen`: Alternar tela branca como quadro de anotações (`W`).
- `ppt_end_show`: Encerrar apresentação de slides (`Esc`).

### 19. Design, Criação & Produtividade (Figma, Canva, Photoshop, PDF, Notion)
- `design_duplicate`: Duplicar objeto ou elemento selecionado (`Ctrl+D`).
- `design_group` / `design_ungroup`: Agrupar (`Ctrl+G`) ou desagrupar (`Ctrl+Shift+G`) elementos.
- `design_zoom_fit`: Ajustar visualização à tela (`Ctrl+0`).
- `design_zoom_selection`: Focar no objeto ou frame selecionado no Figma (`Shift+2`).
- `notion_toggle_list`: Criar lista recolhível / toggle no Notion (`Ctrl+Shift+7`).
- `notion_code_block`: Inserir bloco de código formatado (`Ctrl+Alt+8`).
- `pdf_rotate`: Girar página no visualizador de PDF (`Ctrl+Shift+R`).

### 20. Sistema & Gerenciamento de Energia
- `sleep_pc`: Coloca o PC em modo de suspensão profunda (Sleep S3 - **Modo Recomendado para acordar com a Ignição / Wake-on-LAN em 2s**).
- `shutdown_pc`: Desliga o computador completamente (`shutdown /s /t 3`).
- `taskmgr`: Abre o Gerenciador de Tarefas (`Ctrl+Shift+Esc`).
- `lock_pc`: Bloqueia o computador imediatamente (`Win+L`).
- `turn_off_screens`: Apaga os monitores do PC para economia imediata de energia.
- `restart_explorer`: Reinicia o processo do Windows Explorer e a barra de tarefas.

### 21. 📱 Controle Total do Celular Android (ADB & Dashboard Web na Porta 8080)
Além de controlar o PC pelo celular, o sistema permite controlar o smartphone diretamente pelo navegador do computador através do endereço `http://<ip-celular>:8080/` ou via chamadas REST para `/api/phone/macro/{id}`:
- **Navegação & Sistema**:
  - `home`: Retorna à tela inicial.
  - `back`: Ação de voltar do Android.
  - `recents`: Alternador de aplicativos recentes (Multitarefa).
  - `notifications`: Puxa a cortina de notificações.
  - `quick_settings`: Abre o painel de configurações rápidas.
  - `collapse_panels`: Recolhe todas as barras e notificações abertas.
  - `lock`: Bloqueia a tela do aparelho.
  - `unlock`: Acorda e desbloqueia a tela.
  - `screenshot`: Tira print/captura de tela instantânea do celular.
  - `camera`: Lança a câmera do aparelho em 1 toque.
- **Gestos Táteis & Swipes**:
  - `scroll_up` / `scroll_down`: Rolagem suave vertical.
  - `scroll_left` / `scroll_right`: Deslizar páginas horizontalmente.
  - `scroll_top`: Rola direto para o topo da página/app.
  - `scroll_bottom`: Rola direto para o final do conteúdo.
  - `double_tap`: Simula toque duplo no centro do visor.
- **Mídia, Volume & Localização**:
  - `vol_up` / `vol_down`: Ajuste de volume do Android.
  - `mute`: Silencia o som do smartphone.
  - `play_pause`: Toca ou pausa vídeos e músicas (YouTube, Spotify, etc.).
  - `next_track` / `prev_track`: Próxima ou faixa anterior.
  - `find_phone`: Dispara alarme e vibração contínua para localizar o aparelho no cômodo.
  - `vibrate`: Pulso tátil de vibração no smartphone.
- **Atalhos Rápidos de Aplicativos**:
  - `open_whatsapp`, `open_youtube`, `open_spotify`, `open_chrome`.
  - `open_files`, `open_gallery`, `open_music`, `open_maps`.
  - `open_dialer`, `open_sms`, `open_clock`, `open_calculator`, `open_playstore`.
- **Entrada de Texto & Teclas do Sistema**:
  - `key_enter`, `key_backspace`, `key_space`, `key_search`, `key_tab`, `key_escape`.
  - `paste_clipboard`: Injeta o texto da área de transferência diretamente no campo focado.
- **Configurações do Android**:
  - `open_wifi_settings`, `open_bluetooth_settings`, `open_display_settings`, `open_battery_settings`, `open_sound_settings`, `open_app_manager`.

---

## 🧪 Diagnóstico e Testes

Para validar a integridade de todas as bibliotecas e testar a comunicação com a API:

Execute no terminal:
```bash
python test_server.py
```

O script testa automaticamente:
1. Módulos instalados (`FastAPI`, `Uvicorn`, `PyAutoGUI`, `MSS`, `Pillow`, `psutil`, `pystray`, `pycaw`, `PyAudio`).
2. Resposta e latência de `/api/status`.
3. Informações da placa de rede física para Wake-on-LAN (`/api/wol/info`).
4. Catálogo de macros carregadas (`/api/macros`).
5. Latência de captura de tela em milissegundos (`/api/screen/frame`).
6. Status do autostart no Registro (`/api/autostart/status`).
7. Configurações carregadas do JSON (`/api/config`).
8. Disponibilidade da documentação Swagger OpenAPI (`/docs`).

---

## 📁 Estrutura de Arquivos

```text
├── MacroEngine-1.1.8v.apk        # Instalador Android oficial pronto para uso
├── config.json                  # Arquivo de configurações personalizáveis
├── server.py                    # Servidor principal (FastAPI, sockets, macros, tray)
├── requirements.txt             # Dependências oficiais versionadas
├── setup_environment.bat        # Instalador e configurador de ambiente em 1 clique
├── install_autostart.bat        # Registra a inicialização automática no Windows
├── uninstall_autostart.bat      # Remove a inicialização automática do Windows
├── run_silent.vbs               # Launcher VBScript 100% invisível em segundo plano
├── start_server.bat             # Inicia o servidor em modo console normal
├── start_server_background.bat  # Inicia o servidor silencioso em segundo plano
├── stop_server.bat              # Encerra graciosamente os processos do servidor
├── register_firewall.bat        # Libera portas 8000 e 50005 no Firewall do Windows
├── test_server.py               # Suite de auto-diagnóstico e testes de saúde
├── models/                      # Pasta para modelos de inteligência artificial locais
├── shared_files/                # Pasta de arquivos compartilhados entre PC e Celular
├── LICENSE                      # Licença MIT
└── README.md                    # Documentação completa do projeto
```

---

## ☕ Apoie o Projeto / Contribuição

Se o **MacroEngine** te ajudou ou foi útil no seu dia a dia e você deseja incentivar o desenvolvimento contínuo, novas atualizações e novas macros, qualquer contribuição é muito bem-vinda!

<div align="center">

### 💠 Chave PIX:
```text
41998205303
```
*Muito obrigado pelo apoio à evolução da ferramenta!* 🚀

</div>

---

## 📄 Licença

Este projeto é distribuído sob os termos da licença **MIT**. Consulte o arquivo [LICENSE](LICENSE) para obter detalhes completos.

---

<div align="center">
  <b>MacroEngine</b> • Automação e Controle Total na Palma da Sua Mão.
</div>
