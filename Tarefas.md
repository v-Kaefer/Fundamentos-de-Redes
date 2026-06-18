Abaixo está uma separação prática das etapas do trabalho, na ordem ideal de desenvolvimento. A ideia é começar pelo núcleo obrigatório do anel e só depois adicionar falhas, interface, entrada dinâmica e relatório.

## Etapa 1 — Entendimento e decisões iniciais

Antes de programar, definam:

**Linguagem:** Python, Java, C ou outra permitida pelo professor.
**Execução local:** permitir várias instâncias na mesma máquina, cada uma com uma porta unicast diferente.
**Formato dos pacotes:** seguir exatamente o padrão do enunciado, pois haverá interoperabilidade entre grupos. O trabalho exige mensagens `DISCOVER`, `HELLO`, `TOKEN` e pacotes de dados com campos separados por `:`. 

Decisão importante: implementem tudo em texto puro, por exemplo:

```txt
10:A:192.168.1.10:6001
20:B:192.168.1.11:6002
1000
2000:B:A:maquinainexistente:19385749:Oi pessoal!
```

---

## Etapa 2 — Leitura do arquivo de configuração

Implementar a leitura do `config.txt`.

O arquivo deve conter:

```txt
apelido
tempo_token_dados
probabilidade_erro
timeout_token
tempo_minimo_entre_tokens
porta_unicast
```

Exemplo:

```txt
B
2
20
2.5
2
6002
```

Essa etapa deve gerar uma estrutura interna parecida com:

```txt
apelido = B
tempo_token_dados = 2s
probabilidade_erro = 20%
timeout_token = 2.5s
tempo_minimo_entre_tokens = 2s
porta_unicast = 6002
```

Essa etapa é base para todas as outras.

---

## Etapa 3 — Estrutura base da máquina

Criar a estrutura principal de uma máquina do anel.

Cada instância deve guardar:

```txt
apelido local
IP local
porta unicast local
lista de máquinas conhecidas
sucessor atual
fila de mensagens
estado do token
estado de pacote de dados em trânsito
configuração carregada
```

A fila deve ter limite de até 10 mensagens, conforme o enunciado. 

Sugestão de componentes/classes:

```txt
Config
NodeInfo
RingManager
UdpService
TokenManager
MessageQueue
PacketParser
CrcService
FailureInjector
ConsoleInterface
```

---

## Etapa 4 — Comunicação UDP básica

Implementar primeiro o envio e recebimento UDP sem lógica de Token Ring.

Devem existir dois canais principais:

```txt
porta 6000 — broadcast DISCOVER/HELLO
porta unicast configurada — token e dados
```

Testes desta etapa:

```txt
A envia texto para B
B recebe e imprime
B envia texto para A
A recebe e imprime
broadcast na porta 6000 funciona
cada instância escuta sua própria porta unicast
```

Somente avance depois que a comunicação UDP estiver estável.

---

## Etapa 5 — Descoberta de máquinas

Implementar a fase de descoberta.

Ao iniciar, cada máquina deve enviar:

```txt
10:APELIDO:IP:PORTA
```

Ao receber `DISCOVER`, deve responder com:

```txt
20:APELIDO:IP:PORTA
```

Cada máquina deve montar a lista de máquinas conhecidas.

Exemplo:

```txt
A 192.168.1.10 6001
B 192.168.1.11 6002
C 192.168.1.12 6003
```

Essa descoberta acontece por broadcast na porta 6000, e o enunciado também exige escuta contínua nessa porta para permitir entrada de novas máquinas durante a execução. 

---

## Etapa 6 — Formação do anel

Depois da descoberta, ordenar as máquinas alfabeticamente pelo apelido.

Exemplo:

```txt
A → B → C → D → A
```

Cada máquina deve identificar apenas seu sucessor.

Exemplo:

```txt
A envia para B
B envia para C
C envia para D
D envia para A
```

A primeira máquina em ordem alfabética é responsável por gerar o primeiro token e monitorá-lo. 

---

## Etapa 7 — Implementação do token simples

Criar o pacote:

```txt
1000
```

Regra inicial:

```txt
Recebeu token e não tem mensagem na fila → repassa token ao sucessor.
```

Neste ponto, ainda não precisa enviar dados. O objetivo é apenas ver o token circulando.

Teste esperado:

```txt
A recebeu TOKEN
A enviou TOKEN para B
B recebeu TOKEN
B enviou TOKEN para C
C recebeu TOKEN
C enviou TOKEN para A
```

Essa é uma das etapas mais importantes, porque valida o anel.

---

## Etapa 8 — Fila de mensagens

Implementar a fila local de mensagens.

A interface deve permitir inserir:

```txt
destino
mensagem
```

Exemplo:

```txt
Destino: C
Mensagem: Olá C!
```

Internamente:

```txt
fila = [
  { destino: C, mensagem: "Olá C!", tentativas: 0 }
]
```

Regras:

```txt
máximo de 10 mensagens
envia apenas uma mensagem por passagem de token
se a fila estiver vazia, repassa o token
se a fila tiver mensagem, segura o token e envia pacote de dados
```

---

## Etapa 9 — Envio de pacote de dados

Implementar o pacote:

```txt
2000:origem:destino:controle_erro:CRC:mensagem
```

Quando a máquina recebe o token e tem mensagem na fila, ela deve enviar o pacote de dados ao sucessor e não enviar o token imediatamente.

Exemplo:

```txt
2000:A:C:maquinainexistente:123456789:Oi C!
```

Regra:

```txt
o dado circula pelo anel até retornar à origem
somente depois disso o token volta a circular
```

Esse comportamento está descrito no funcionamento do anel: uma máquina com dados envia o pacote e o token fica retido até o dado completar a volta. 

---

## Etapa 10 — Comportamento no destino

Quando uma máquina recebe pacote de dados:

### Caso 1 — Não é o destino

Repassa sem alterar:

```txt
recebi pacote para C, mas sou B
repassando para próximo
```

### Caso 2 — É o destino

Deve:

```txt
recalcular CRC32
mostrar origem e mensagem na tela
alterar controle_erro para ACK ou NAK
repassar pacote ao próximo
```

Resultado possível:

```txt
2000:A:C:ACK:123456789:Oi C!
```

ou:

```txt
2000:A:C:NAK:123456789:Oi C!
```

---

## Etapa 11 — Comportamento na origem quando o pacote retorna

Quando o pacote volta para quem enviou:

### Se voltou com `ACK`

```txt
mensagem entregue com sucesso
remove da fila
envia token ao próximo
```

### Se voltou com `NAK`

```txt
erro detectado
mantém mensagem na fila
marca para retransmissão
envia token ao próximo
```

Na próxima vez que essa máquina receber o token, ela retransmite a mensagem. Segundo o enunciado, a retransmissão ocorre apenas uma vez; se falhar novamente, a mensagem é descartada. 

### Se voltou com `maquinainexistente`

```txt
destino não encontrado no anel
remove da fila
envia token ao próximo
```

---

## Etapa 12 — CRC32

Implementar cálculo de CRC32 sobre o conteúdo da mensagem.

A origem calcula o CRC antes de enviar:

```txt
mensagem = "Oi C!"
CRC32 = 123456789
```

O destino recalcula:

```txt
CRC recebido == CRC calculado → ACK
CRC recebido != CRC calculado → NAK
```

Essa etapa deve ser isolada em uma função ou classe, para facilitar teste.

---

## Etapa 13 — Inserção de falhas

Implementar o módulo de erro aleatório.

Fluxo:

```txt
origem calcula CRC da mensagem original
módulo de falha pode alterar a mensagem antes do envio
destino recalcula CRC da mensagem recebida
se a mensagem foi alterada, o CRC não bate
destino devolve NAK
```

A probabilidade vem do arquivo de configuração.

Exemplo:

```txt
Mensagem original: Olá mundo
CRC calculado: 999999
Mensagem enviada com erro: Olá muxdo
Destino calcula CRC diferente
Retorna NAK
```

Importante: o broadcast não deve sofrer inserção de falhas, conforme o enunciado. 

---

## Etapa 14 — Broadcast de mensagens

Implementar envio para:

```txt
destino = BROADCAST
```

Regras:

```txt
todos exibem a mensagem
controle_erro permanece maquinainexistente
não aplica módulo de falhas
pacote circula até voltar à origem
origem remove da fila e libera token
```

Exemplo:

```txt
2000:A:BROADCAST:maquinainexistente:123456789:Olá todos!
```

---

## Etapa 15 — Controle de token perdido

A máquina que gerou o primeiro token deve monitorar se o token passa por ela dentro do timeout configurado.

Situação:

```txt
A é a primeira máquina
A criou o token
A espera o token voltar
se passar do timeout, considera token perdido
A gera novo token
```

Deve haver aviso na interface:

```txt
Token perdido detectado. Novo token gerado.
```

---

## Etapa 16 — Controle de token duplicado

A máquina geradora também deve verificar se o token voltou cedo demais.

Regra:

```txt
se o token chega antes do tempo mínimo entre tokens
há token duplicado
remove o token extra
```

Aviso esperado:

```txt
Token duplicado detectado. Token extra removido.
```

---

## Etapa 17 — Opções manuais de token

A interface deve permitir:

```txt
retirar token da rede
inserir token na rede
```

Essas opções servem para demonstrar falhas na apresentação.

Menu sugerido:

```txt
1 - Enviar mensagem
2 - Enviar broadcast
3 - Retirar token da rede
4 - Inserir token na rede
5 - Mostrar estado do anel
6 - Mostrar fila local
0 - Sair
```

---

## Etapa 18 — Entrada de nova máquina no anel

Implementar entrada dinâmica.

Cenário:

```txt
A, B e C já estão rodando
D inicia depois
D envia DISCOVER
A, B e C respondem HELLO
todos recalculam o anel
novo anel: A → B → C → D → A
```

Restrição importante:

```txt
nova máquina só pode entrar quando somente o token estiver circulando
não pode haver pacote de dados em trânsito
```

Essa etapa é mais avançada. Deve ser feita depois que token, dados e fila já estiverem funcionando.

---

## Etapa 19 — Interface em modo texto

A interface precisa mostrar:

```txt
fila de mensagens
token recebido/enviado
pacote de dados recebido/enviado
ACK
NAK
retransmissão
token perdido
token duplicado
estado do anel
sucessor atual
máquinas conhecidas
```

O enunciado exige que a interface permita enviar mensagens a qualquer momento, retirar/inserir token, visualizar token e dados, exibir retransmissões e informar o estado do anel. 

---

## Etapa 20 — Testes locais

Testar em uma máquina com várias instâncias.

Exemplo:

```txt
Instância A → porta 6001
Instância B → porta 6002
Instância C → porta 6003
Broadcast → porta 6000
```

Casos de teste obrigatórios:

```txt
A descobre B e C
anel forma A → B → C → A
token circula sem mensagens
A envia unicast para C
C responde ACK
A envia para máquina inexistente
A envia broadcast
falha gera NAK
mensagem é retransmitida
token é retirado manualmente
timeout gera novo token
token duplicado é detectado
nova máquina entra durante execução
```

---

## Etapa 21 — Testes em máquinas diferentes

Depois dos testes locais, testar em pelo menos 3 máquinas na mesma rede Wi-Fi.

Verificar:

```txt
broadcast funciona na rede real
firewall não bloqueia UDP
IPs são detectados corretamente
portas estão liberadas
implementações de grupos diferentes conseguem conversar
```

A apresentação exige no mínimo 3 máquinas na mesma rede Wi-Fi e demonstração de unicast, broadcast, erro, retransmissão, controle de token e entrada de novas máquinas. 

---

## Etapa 22 — Relatório

O relatório deve explicar:

```txt
estrutura da solução
estruturas de dados
threads/classes
mecanismos de sincronização
CRC32
exemplos de execução
evidências de captura
```

Sugestão de seções:

```txt
1. Introdução
2. Arquitetura da solução
3. Formato dos pacotes
4. Descoberta e formação do anel
5. Circulação do token
6. Envio unicast e broadcast
7. CRC32 e controle de erro
8. Inserção de falhas
9. Controle de token perdido e duplicado
10. Entrada dinâmica de máquinas
11. Testes realizados
12. Evidências de execução
13. Conclusão
```

---

## Etapa 23 — Preparação da apresentação

Preparar uma demonstração com roteiro.

Ordem recomendada:

```txt
1. Mostrar três instâncias/máquinas iniciando
2. Mostrar DISCOVER/HELLO
3. Mostrar formação do anel
4. Mostrar token circulando
5. Enviar unicast com ACK
6. Enviar broadcast
7. Simular erro e mostrar NAK
8. Mostrar retransmissão
9. Retirar token e mostrar recuperação
10. Inserir token extra e mostrar detecção de duplicado
11. Adicionar nova máquina ao anel
12. Explicar estruturas/classes principais
```

---

## Ordem ideal de implementação

A ordem mais segura é esta:

```txt
1. Configuração
2. UDP básico
3. DISCOVER/HELLO
4. Lista ordenada e sucessor
5. Token circulando
6. Fila de mensagens
7. Pacote de dados
8. ACK/maquinainexistente
9. CRC32
10. NAK
11. Retransmissão
12. Inserção de falhas
13. Broadcast
14. Interface completa
15. Token perdido
16. Token duplicado
17. Entrada dinâmica de máquina
18. Testes locais
19. Testes em Wi-Fi
20. Relatório
21. Roteiro de apresentação
```

---

## Divisão sugerida para grupo de até 4 pessoas

### Pessoa 1 — Rede e descoberta

```txt
UDP unicast
UDP broadcast
DISCOVER
HELLO
lista de máquinas
formação do anel
```

### Pessoa 2 — Token e anel

```txt
circulação do token
sucessor
controle de token retido
token perdido
token duplicado
inserção/remoção manual de token
```

### Pessoa 3 — Mensagens e erros

```txt
fila de mensagens
pacote 2000
unicast
broadcast
CRC32
inserção de falhas
ACK/NAK
retransmissão
```

### Pessoa 4 — Interface, testes e relatório

```txt
menu em texto
logs de estado
evidências de execução
testes com 3 máquinas
relatório
roteiro de apresentação
```

---

## Observação importante

A rubrica do PDF menciona itens como “raw sockets”, “arquivos CSV” e “interface com contadores”, mas o enunciado principal descreve uma aplicação UDP Token Ring com pacotes em texto, fila, CRC32, controle de token e relatório. Isso parece uma inconsistência do documento. Vale confirmar com o professor se a rubrica correta é essa ou se ficou de outro trabalho.
