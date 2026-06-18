# Análise e plano de desenvolvimento — Simulador de Rede em Anel com Token

## 1. Visão geral do trabalho

O trabalho pede a implementação de uma aplicação que simule uma rede local em anel com passagem de token, usando UDP como transporte. Cada máquina deve participar de um anel lógico, descobrir as demais máquinas via broadcast, transmitir mensagens respeitando a posse do token, tratar erro por CRC32, permitir retransmissão em caso de `NAK`, controlar perda/duplicação de token e aceitar entrada de novas máquinas durante a execução.

O ponto mais importante do trabalho não é apenas fazer uma simulação local funcionar, mas garantir **interoperabilidade** com implementações de outros grupos durante a apresentação. Por isso, o desenvolvimento deve priorizar:

1. aderência exata ao formato dos pacotes;
2. robustez no parser;
3. comportamento previsível do token;
4. logs claros para demonstração;
5. testes em múltiplas instâncias e, depois, em máquinas reais na mesma rede Wi-Fi.

---

## 2. Requisitos principais extraídos do enunciado

### 2.1 Funcionalidades obrigatórias

A aplicação deve:

- ler um arquivo de configuração com:
  - apelido da máquina;
  - tempo do token e dos dados;
  - probabilidade de erro nas mensagens;
  - timeout do token;
  - tempo mínimo entre tokens;
  - porta de escuta unicast;
- descobrir máquinas via `DISCOVER` em broadcast na porta `6000`;
- responder descobertas com `HELLO`, também em broadcast;
- formar o anel ordenando as máquinas por apelido;
- enviar token e dados sempre para o sucessor;
- manter fila de até 10 mensagens;
- enviar mensagens unicast e broadcast;
- calcular CRC32 da mensagem original;
- inserir falhas aleatórias conforme probabilidade configurada;
- detectar erro no destino e responder com `ACK` ou `NAK`;
- retransmitir uma mensagem apenas uma vez em caso de `NAK`;
- descartar mensagem após nova falha;
- detectar destino inexistente;
- monitorar perda e duplicação de token;
- permitir remoção e inserção manual de token;
- aceitar entrada de novas máquinas durante a execução;
- exibir estado do anel, token, dados, retransmissões e eventos relevantes;
- funcionar em pelo menos 3 máquinas na apresentação.

### 2.2 Pacotes obrigatórios

Todos os pacotes devem ser texto puro, separados por `:`.

```text
DISCOVER:
10:<apelido>:<IP>:<porta>

HELLO:
20:<apelido>:<IP>:<porta>

TOKEN:
1000

DADOS:
2000:<origem>:<destino>:<controle_erro>:<CRC>:<mensagem>
```

Valores válidos para `controle_erro`:

```text
maquinainexistente
ACK
NAK
```

O destino pode ser um apelido, por exemplo `A`, `B`, `C`, ou o valor especial:

```text
BROADCAST
```

---

## 3. Ponto crítico: interoperabilidade

A interoperabilidade deve ser tratada como prioridade desde o início. O programa pode ter logs, interface bonita e comandos extras, mas os pacotes enviados pela rede devem seguir estritamente o padrão do enunciado.

### 3.1 Regras práticas para evitar incompatibilidade

- Não adicionar campos extras aos pacotes.
- Não adicionar espaços antes ou depois dos `:`.
- Usar exatamente os códigos:
  - `10`;
  - `20`;
  - `1000`;
  - `2000`.
- Usar exatamente `BROADCAST`, em maiúsculas.
- Usar exatamente `maquinainexistente`, `ACK` e `NAK`.
- Usar UTF-8 para codificar a mensagem.
- Calcular o CRC32 sobre os bytes UTF-8 da mensagem.
- Ao fazer parse de pacote de dados, dividir a string em no máximo 6 partes:
  - tipo;
  - origem;
  - destino;
  - controle;
  - CRC;
  - mensagem.
- Isso evita erro quando a mensagem contém `:` no texto.

Exemplo correto de parser conceitual:

```text
2000:B:A:maquinainexistente:19385749:Oi: teste
```

Deve ser interpretado como:

```text
tipo = 2000
origem = B
destino = A
controle = maquinainexistente
crc = 19385749
mensagem = Oi: teste
```

---

## 4. Melhor estratégia de desenvolvimento

A melhor abordagem é desenvolver em camadas, validando cada parte antes de avançar. O trabalho possui muitas regras de rede e concorrência; tentar implementar tudo de uma vez aumenta muito o risco de bugs difíceis de rastrear.

A sequência recomendada é:

1. implementar configuração, modelo de dados e parser;
2. implementar descoberta via UDP broadcast;
3. montar o anel e identificar sucessor;
4. fazer o token circular sem mensagens;
5. adicionar fila de mensagens e envio de dados;
6. implementar retorno à origem;
7. implementar CRC32, `ACK`, `NAK` e retransmissão;
8. implementar broadcast;
9. implementar controle de perda/duplicação de token;
10. implementar alteração topológica;
11. melhorar interface;
12. gerar logs/evidências;
13. testar interoperabilidade.

---

## 5. Linguagem e tecnologias recomendadas

Se a disciplina não exigir uma linguagem específica, uma escolha prática para desenvolver rápido é **Python 3**, usando apenas biblioteca padrão:

- `socket` para UDP unicast e broadcast;
- `threading` para escutas simultâneas;
- `queue.Queue` para fila de mensagens;
- `zlib.crc32` para CRC32;
- `time` para temporizações;
- `dataclasses` para estruturas;
- `csv` para logs;
- `argparse` para escolher arquivo de configuração.

Vantagens:

- implementação rápida;
- fácil teste com várias instâncias;
- CRC32 já disponível;
- UDP simples;
- boa produtividade para interface em terminal.

Alternativas viáveis:

- **Java**: bom para disciplina, threads e sockets estáveis, mas mais verboso.
- **C/C++**: maior controle sobre sockets, mas mais propenso a bugs de memória e parsing.
- **Node.js**: simples para UDP, mas menos comum em trabalhos de redes tradicionais.

A recomendação principal é: **usar a linguagem em que o grupo consegue explicar melhor a implementação na apresentação**, porque a rubrica dá grande peso para demonstração de conhecimento.

---

## 6. Arquitetura recomendada

### 6.1 Componentes principais

Uma arquitetura modular reduz bugs e facilita explicar o trabalho.

```text
src/
  main
  config
  protocol
  crc
  network
  discovery
  ring
  token
  message_queue
  fault_injector
  ui
  logger
```

### 6.2 Responsabilidades por módulo

| Módulo | Responsabilidade |
|---|---|
| `config` | Ler e validar o arquivo de configuração. |
| `protocol` | Montar e decodificar pacotes `10`, `20`, `1000` e `2000`. |
| `crc` | Calcular CRC32 da mensagem. |
| `network` | Enviar e receber UDP unicast/broadcast. |
| `discovery` | Enviar `DISCOVER`, responder com `HELLO` e manter escuta na porta `6000`. |
| `ring` | Manter lista de máquinas, ordenar apelidos e calcular sucessor. |
| `token` | Processar chegada do token, perda, duplicação, inserção e remoção. |
| `message_queue` | Gerenciar fila de até 10 mensagens. |
| `fault_injector` | Corromper mensagem de forma probabilística, quando permitido. |
| `ui` | Ler comandos do usuário e exibir estado. |
| `logger` | Registrar eventos, pacotes e evidências. |

---

## 7. Modelo de dados sugerido

### 7.1 Configuração local

```text
Config:
  nickname: str
  token_data_delay_seconds: float
  error_probability_percent: float
  token_timeout_seconds: float
  min_token_interval_seconds: float
  unicast_port: int
```

### 7.2 Máquina conhecida

```text
Machine:
  nickname: str
  ip: str
  port: int
  last_seen: timestamp
```

### 7.3 Estado do anel

```text
RingState:
  local_nickname: str
  machines: dict[nickname, Machine]
  ordered_nicknames: list[str]
  successor: Machine
  generator_nickname: str
  pending_topology_update: bool
```

### 7.4 Mensagem da fila

```text
QueuedMessage:
  destination: str
  original_message: str
  original_crc32: int
  retry_count: int
```

### 7.5 Estado do token

```text
TokenState:
  last_token_seen_at: timestamp
  last_token_forwarded_at: timestamp
  discard_next_token: bool
  manually_inserted_tokens: int
```

---

## 8. Threads recomendadas

O programa deve fazer várias coisas ao mesmo tempo: escutar broadcast, escutar unicast, receber comando do usuário e monitorar o token. Por isso, uma implementação com threads é adequada.

### 8.1 Threads mínimas

| Thread | Função |
|---|---|
| `broadcast_listener` | Escuta contínua na porta `6000` para `DISCOVER` e `HELLO`. |
| `unicast_listener` | Escuta na porta local configurada para token e dados. |
| `ui_thread` | Lê comandos do usuário sem bloquear a rede. |
| `token_monitor` | Apenas na máquina geradora, detecta token perdido ou duplicado. |

### 8.2 Sincronização

As estruturas compartilhadas devem ser protegidas por lock/mutex:

- lista de máquinas conhecidas;
- sucessor atual;
- fila de mensagens;
- estado do token;
- flags de alteração topológica;
- logs compartilhados.

Em Python, por exemplo, isso pode ser feito com:

```text
threading.Lock
queue.Queue
threading.Event
```

---

## 9. Fluxo de inicialização recomendado

### 9.1 Passo a passo

1. Ler `config.txt`.
2. Validar valores.
3. Abrir socket de broadcast na porta `6000`.
4. Abrir socket unicast na porta configurada.
5. Registrar a própria máquina na lista local.
6. Iniciar thread de escuta broadcast.
7. Iniciar thread de escuta unicast.
8. Enviar `DISCOVER`.
9. Aguardar pequena janela de descoberta, por exemplo 2 a 5 segundos.
10. Ordenar máquinas por apelido.
11. Calcular sucessor.
12. Se a máquina local for a primeira da ordem alfabética, gerar o primeiro token.
13. Iniciar interface de usuário.

### 9.2 Observação importante

A escuta na porta `6000` não pode parar depois da inicialização, porque o enunciado exige entrada de novas máquinas durante a execução.

---

## 10. Funcionamento do token

### 10.1 Regra central

Somente quem recebe o token pode transmitir uma mensagem da fila. Se não houver mensagem, o token é apenas repassado.

### 10.2 Fluxo recomendado ao receber token

```text
ao_receber_token():
  se máquina local é geradora:
    verificar se token chegou cedo demais
    se chegou antes do tempo mínimo:
      registrar token duplicado
      descartar token
      retornar

  se usuário pediu remoção manual de token:
    descartar este token
    registrar evento
    retornar

  aplicar atualização topológica pendente, se for seguro

  aguardar tempo configurado para token/dados

  se fila local tem mensagem:
    retirar ou consultar primeira mensagem da fila
    montar pacote de dados
    enviar dados ao sucessor
    não enviar token agora
  senão:
    enviar token ao sucessor
```

A mensagem não deve ser removida definitivamente da fila no momento do envio. Ela só deve sair da fila quando voltar com `ACK`, quando voltar com `maquinainexistente`, ou quando falhar novamente após uma retransmissão.

---

## 11. Funcionamento dos dados

### 11.1 Recebimento por máquina intermediária

Se a máquina local não é o destino e também não é a origem, ela apenas repassa o pacote para o sucessor.

```text
se pacote.origem != local e pacote.destino != local e pacote.destino != BROADCAST:
  repassar sem alteração
```

### 11.2 Recebimento pelo destino

Se a máquina local é o destino:

1. recalcular CRC32 da mensagem recebida;
2. comparar com o CRC do pacote;
3. exibir origem e mensagem;
4. alterar controle para:
   - `ACK`, se CRC confere;
   - `NAK`, se CRC não confere;
5. repassar pacote ao sucessor.

### 11.3 Retorno à origem

Quando o pacote retorna à origem:

| Controle | Ação |
|---|---|
| `ACK` | Exibir sucesso, remover mensagem da fila e enviar token ao sucessor. |
| `NAK` | Se ainda não retransmitiu, manter mensagem na fila, marcar uma tentativa e enviar token. |
| `NAK` novamente | Descartar mensagem, avisar usuário e enviar token. |
| `maquinainexistente` | Informar que destino não está na rede, remover mensagem da fila e enviar token. |

---

## 12. CRC32 e inserção de falhas

### 12.1 Ordem correta

Para o teste de erro funcionar, a ordem deve ser:

1. calcular CRC32 da mensagem original;
2. montar pacote com mensagem original;
3. se a mensagem for unicast e a probabilidade indicar erro, corromper a mensagem no pacote;
4. enviar pacote com CRC original e mensagem possivelmente corrompida.

Se o CRC for recalculado depois da corrupção, o destino não detectará erro. Portanto, o CRC precisa representar a mensagem original.

### 12.2 Broadcast

Para mensagens broadcast:

- não aplicar inserção de falhas;
- manter controle como `maquinainexistente`;
- exibir a mensagem nas máquinas participantes;
- ao retornar à origem, considerar a transmissão encerrada e liberar o token.

---

## 13. Tratamento de retransmissão

A retransmissão deve ocorrer apenas uma vez.

Modelo sugerido:

```text
retry_count = 0

se pacote retorna com NAK:
  se retry_count == 0:
    retry_count = 1
    manter mensagem na fila
    enviar token
  senão:
    descartar mensagem
    enviar token
```

Na próxima vez que a origem receber o token, ela envia novamente a mesma mensagem original, com:

```text
controle_erro = maquinainexistente
CRC = CRC32(mensagem original)
mensagem = mensagem original
```

---

## 14. Controle de token perdido e duplicado

A primeira máquina da ordem alfabética é responsável por gerar o token inicial e monitorar o funcionamento.

### 14.1 Token perdido

A máquina geradora deve controlar quando viu o token pela última vez. Se o token não passar por ela dentro do timeout configurado, deve gerar um novo token.

Ponto de atenção: durante a circulação de dados, o token fica retido até o dado voltar à origem. Portanto, o timeout deve ser configurado com folga suficiente para não gerar falsos positivos. Uma implementação mais segura deve registrar atividade do anel e evitar recriar token enquanto houver pacote de dados claramente em trânsito.

### 14.2 Token duplicado

Se a máquina geradora receber um token antes do tempo mínimo configurado entre tokens, deve considerar que há duplicação e descartar o token extra.

### 14.3 Remoção manual de token

Como o token não está centralizado, a remoção manual pode ser implementada assim:

```text
comando_usuario_remover_token:
  discard_next_token = true
```

Quando o próximo token chegar à máquina local, ele é descartado e não repassado.

### 14.4 Inserção manual de token

A inserção manual pode enviar imediatamente um pacote `1000` ao sucessor.

Isso é útil para demonstrar:

- recuperação após perda;
- geração de token duplicado;
- detecção pelo monitor.

---

## 15. Alteração topológica durante execução

O enunciado exige que uma nova máquina entre sem reiniciar a rede, desde que somente o token esteja circulando, sem dados em trânsito.

### 15.1 Estratégia simples e segura

1. Nova máquina envia `DISCOVER`.
2. Máquinas existentes respondem `HELLO`.
3. Todas adicionam a nova máquina à lista conhecida.
4. Marcam `pending_topology_update = true`.
5. A atualização do sucessor é aplicada quando o token passa pela máquina, pois esse é o momento em que não há dado sendo processado localmente.
6. A máquina recalcula a ordem e encaminha o token para o sucessor atualizado.

Essa estratégia reduz o risco de quebrar o caminho de um pacote de dados que já estava circulando.

### 15.2 Atenção

A entrada dinâmica é uma das partes mais arriscadas. Deve ser testada cedo, não apenas no final.

---

## 16. Interface em modo texto

A interface não precisa ser gráfica. Uma interface textual boa e clara é suficiente.

### 16.1 Comandos recomendados

```text
send <destino> <mensagem>
broadcast <mensagem>
queue
ring
state
drop-token
insert-token
help
exit
```

### 16.2 Informações exibidas

A tela deve mostrar:

- apelido local;
- IP local;
- porta unicast;
- lista ordenada do anel;
- sucessor atual;
- tamanho da fila;
- último token visto;
- último pacote de dados visto;
- mensagens recebidas;
- retransmissões;
- `ACK`;
- `NAK`;
- destino inexistente;
- token perdido;
- token duplicado;
- alteração topológica.

---

## 17. Logs e evidências

O relatório precisa incluir evidências de execução. Além disso, a rubrica menciona geração de CSV, embora o enunciado não detalhe o formato desses arquivos. Para reduzir risco, recomenda-se implementar CSVs simples e úteis.

### 17.1 Arquivos CSV sugeridos

#### `packets.csv`

```text
timestamp,local,event,type,direction,src,dst,control,crc,message_preview,next_hop_ip,next_hop_port
```

Eventos possíveis:

```text
RECV_DISCOVER
SEND_DISCOVER
RECV_HELLO
SEND_HELLO
RECV_TOKEN
SEND_TOKEN
DROP_TOKEN
RECV_DATA
SEND_DATA
FORWARD_DATA
ACK
NAK
DEST_NOT_FOUND
```

#### `ring_state.csv`

```text
timestamp,local,members,successor,queue_size,last_token_seen,last_event
```

Esses arquivos ajudam na apresentação e também atendem preventivamente à rubrica.

### 17.2 Capturas recomendadas para o relatório

- terminal mostrando descoberta das máquinas;
- terminal mostrando formação do anel;
- envio unicast com `ACK`;
- envio para máquina inexistente;
- envio broadcast;
- erro forçado com `NAK`;
- retransmissão bem-sucedida;
- descarte após segunda falha;
- remoção manual de token;
- inserção manual de token;
- detecção de token duplicado;
- entrada de nova máquina;
- captura no Wireshark ou `tcpdump`, se possível.

---

## 18. Plano de testes

### 18.1 Testes locais em uma máquina

Executar múltiplas instâncias com portas diferentes:

```text
A -> porta 6001
B -> porta 6002
C -> porta 6003
D -> porta 6004
```

Todas escutam broadcast na porta `6000`.

### 18.2 Casos mínimos de teste

| Caso | O que testar | Resultado esperado |
|---|---|---|
| T1 | Inicializar A, B e C | Todos descobrem todos e formam `A -> B -> C -> A`. |
| T2 | Token sem mensagens | Token circula continuamente. |
| T3 | Envio A para B | B exibe mensagem, A recebe `ACK`. |
| T4 | Envio A para Z | Pacote volta com `maquinainexistente`. |
| T5 | Broadcast A | B e C exibem mensagem, sem `ACK`/`NAK`. |
| T6 | Erro forçado em unicast | Destino retorna `NAK`. |
| T7 | Retransmissão | Mensagem é reenviada uma vez. |
| T8 | Segunda falha | Mensagem é descartada. |
| T9 | Remover token | Anel para de circular token. |
| T10 | Inserir token | Anel volta a circular. |
| T11 | Inserir token extra | Geradora detecta duplicação. |
| T12 | Entrar D em execução | Todos recalculam o anel. |
| T13 | Testar em Wi-Fi real | Máquinas diferentes comunicam usando IPs reais. |
| T14 | Interoperabilidade | Comunicar com implementação de outro grupo. |

---

## 19. Riscos técnicos e como reduzir

| Risco | Impacto | Como reduzir |
|---|---:|---|
| Parser incompatível | Alto | Implementar testes unitários com todos os exemplos do enunciado. |
| Broadcast não funciona em algumas redes | Alto | Testar cedo no Wi-Fi da apresentação e permitir configurar endereço de broadcast se necessário. |
| Múltiplas instâncias não recebem broadcast local | Médio | Usar `SO_REUSEADDR` e `SO_REUSEPORT` quando disponível. |
| Token duplicado por falso timeout | Alto | Configurar timeout com folga e registrar dados em trânsito. |
| Atualização topológica quebra pacote em trânsito | Alto | Aplicar atualização apenas na passagem do token. |
| Mensagem com `:` quebra parser | Médio | Usar split limitado no pacote de dados. |
| CRC diferente entre grupos | Alto | Padronizar UTF-8 e CRC32 unsigned. |
| Interface bloqueia rede | Alto | Separar interface e sockets em threads. |
| Falta de evidências no relatório | Médio | Gerar logs e prints desde os primeiros testes. |
| Rubrica menciona CSV sem especificar formato | Médio | Implementar CSV próprio e perguntar ao professor se há formato esperado. |

---

## 20. Cronograma recomendado

### Etapa 1 — Base do protocolo

Objetivo: garantir que os pacotes são montados e lidos corretamente.

Entregas:

- leitor de configuração;
- classes/estruturas de pacote;
- parser;
- serialização;
- CRC32;
- testes de parser.

### Etapa 2 — Descoberta e formação do anel

Objetivo: várias instâncias se descobrirem e calcularem o mesmo anel.

Entregas:

- socket broadcast;
- `DISCOVER`;
- `HELLO`;
- lista ordenada;
- cálculo de sucessor;
- logs de estado.

### Etapa 3 — Token básico

Objetivo: token circular sem mensagens.

Entregas:

- envio/recebimento do pacote `1000`;
- delay configurado;
- visualização do token;
- geração inicial pela primeira máquina.

### Etapa 4 — Mensagens unicast

Objetivo: uma máquina enviar uma mensagem para outra usando o token.

Entregas:

- fila de até 10 mensagens;
- pacote `2000`;
- encaminhamento intermediário;
- detecção no destino;
- retorno à origem;
- liberação do token.

### Etapa 5 — CRC, erro e retransmissão

Objetivo: demonstrar `ACK`, `NAK` e retransmissão.

Entregas:

- módulo de falhas;
- CRC original;
- `ACK`;
- `NAK`;
- retransmissão única;
- descarte na segunda falha.

### Etapa 6 — Broadcast

Objetivo: envio para todos os participantes.

Entregas:

- destino `BROADCAST`;
- exibição em todos os nós;
- sem módulo de falhas;
- sem alteração para `ACK`/`NAK`.

### Etapa 7 — Controle do token

Objetivo: demonstrar perda e duplicação.

Entregas:

- timeout de token;
- tempo mínimo entre tokens;
- remoção manual;
- inserção manual;
- logs de perda/duplicação.

### Etapa 8 — Entrada dinâmica

Objetivo: nova máquina entrar sem reiniciar o anel.

Entregas:

- escuta contínua na porta `6000`;
- atualização pendente;
- recálculo de sucessor;
- teste com nova instância durante execução.

### Etapa 9 — Relatório e apresentação

Objetivo: preparar entrega e defesa.

Entregas:

- README;
- relatório;
- prints;
- CSVs;
- roteiro de demonstração;
- perguntas e respostas técnicas prováveis.

---

## 21. Checklist de entrega

### Código

- [ ] Código compila/executa sem erro.
- [ ] Configuração lida corretamente.
- [ ] UDP broadcast funciona.
- [ ] UDP unicast funciona.
- [ ] Pacotes seguem formato exato.
- [ ] Token circula.
- [ ] Fila respeita limite de 10 mensagens.
- [ ] Unicast funciona.
- [ ] Broadcast funciona.
- [ ] CRC32 funciona.
- [ ] Módulo de falhas funciona.
- [ ] `ACK` funciona.
- [ ] `NAK` funciona.
- [ ] Retransmissão ocorre uma vez.
- [ ] Destino inexistente é detectado.
- [ ] Token perdido é detectado.
- [ ] Token duplicado é detectado.
- [ ] Remoção manual de token funciona.
- [ ] Inserção manual de token funciona.
- [ ] Nova máquina entra em execução.
- [ ] Interface mostra estado do anel.
- [ ] Logs/CSVs são gerados.

### Relatório

- [ ] Explica estrutura da solução.
- [ ] Explica threads/classes/módulos.
- [ ] Explica estruturas de dados.
- [ ] Explica sincronização.
- [ ] Explica CRC32.
- [ ] Mostra exemplos de execução.
- [ ] Mostra evidências de captura.
- [ ] Mostra unicast.
- [ ] Mostra broadcast.
- [ ] Mostra erro e retransmissão.
- [ ] Mostra perda/duplicação de token.
- [ ] Mostra entrada de nova máquina.
- [ ] Discute limitações conhecidas.

### Apresentação

- [ ] Pelo menos 3 máquinas na mesma rede Wi-Fi.
- [ ] Todos os integrantes sabem explicar o fluxo.
- [ ] Todos sabem explicar token.
- [ ] Todos sabem explicar CRC.
- [ ] Todos sabem explicar retransmissão.
- [ ] Todos sabem explicar descoberta.
- [ ] Todos sabem explicar alteração topológica.
- [ ] Existe roteiro de demonstração.
- [ ] Existem configurações prontas para A, B, C e D.
- [ ] Existe plano B para rede Wi-Fi instável.

---

## 22. Pontos que devem ser confirmados com o professor

Alguns pontos do enunciado/rubrica merecem confirmação para evitar perda de nota:

1. A rubrica menciona **geração de arquivos CSV**, mas o enunciado não define formato obrigatório.
2. A rubrica menciona **raw sockets**, mas o corpo do trabalho descreve uso de UDP. É importante confirmar se “raw sockets” significa apenas sockets UDP puros, sem biblioteca de alto nível, ou se realmente espera captura em nível mais baixo.
3. O formato do CRC32 deve ser confirmado como inteiro decimal unsigned.
4. Deve-se confirmar se mensagens podem conter `:`. A implementação recomendada suporta isso.
5. Deve-se confirmar se haverá IP de broadcast específico na rede da apresentação ou se `255.255.255.255` será aceito.
6. Deve-se confirmar se a entrada dinâmica precisa de algum protocolo adicional de estabilização ou apenas `DISCOVER`/`HELLO`.

---

## 23. Recomendação final

O melhor caminho é construir primeiro um núcleo pequeno, correto e interoperável. Interface, logs e melhorias devem vir depois que o fluxo principal estiver funcionando.

A ordem de prioridade deve ser:

1. protocolo correto;
2. descoberta correta;
3. anel correto;
4. token correto;
5. dados corretos;
6. CRC/retransmissão;
7. controle de token;
8. entrada dinâmica;
9. interface e relatório.

A parte que mais pode diferenciar o trabalho na apresentação é a clareza dos logs e a capacidade do grupo de explicar o ciclo completo:

```text
token -> origem envia dados -> dado circula -> destino valida CRC -> dado volta à origem -> origem libera token
```

Se esse ciclo estiver sólido, o restante do trabalho fica muito mais fácil de demonstrar e defender.
