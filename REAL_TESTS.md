# Roteiro de Testes Reais

Este roteiro assume 3 PCs Windows no mesmo Wi-Fi, com Python instalado e o
mesmo projeto copiado em cada maquina.

## 1. Preflight por maquina

Rodar em cada maquina:

```bash
python scripts/preflight_check.py --config configs/A.txt
```

Validar:

- Python carregou o projeto sem erro
- config foi lida com sucesso
- IP local foi detectado
- bind UDP funcionou para `6000` e para a porta unicast do perfil
- pasta `logs/` esta gravavel

Se o broadcast `255.255.255.255` falhar no Wi-Fi, repetir os testes com
`--broadcast <ip_de_broadcast_da_subrede>`.

## 2. Perfis de execucao

Usar:

- `A.txt` na maquina A
- `B.txt` na maquina B
- `C.txt` na maquina C
- `D.txt` apenas no teste de entrada dinamica

Perfis de erro:

- `A_err100.txt`
- `B_err100.txt`
- `C_err100.txt`
- `D_err100.txt`

## 3. Subida inicial

Abrir um terminal por maquina:

```bash
python -m src.main --config configs/A.txt
python -m src.main --config configs/B.txt
python -m src.main --config configs/C.txt
```

Em cada terminal:

```text
ring
state
```

Esperado:

- todos mostram o mesmo anel
- `A` vira lider
- o token comeca a circular

Evidencias:

- print do terminal com `ring`
- `logs/packets_*.csv`
- `logs/ring_*.csv`

## 4. Casos obrigatorios

### T1 - Token sem mensagens

- aguardar 20 a 30 segundos
- esperado: circulacao continua, sem recriacao indevida

### T2 - Unicast com ACK

Em `A`:

```text
send B teste-ack-1
```

Esperado:

- `B` exibe a mensagem
- `A` registra `ACK de B`

### T3 - Destino inexistente

Em `A`:

```text
send Z teste-miss-1
```

Esperado:

- a origem informa destino inexistente
- o item sai da fila

### T4 - Broadcast

Em `A`:

```text
broadcast teste-bcast-1
```

Esperado:

- `B` e `C` exibem a mensagem
- a origem encerra o broadcast sem `ACK` ou `NAK`

### T5 - NAK e retransmissao

Reiniciar apenas a origem com perfil `*_err100.txt`.

Exemplo:

```bash
python -m src.main --config configs/A_err100.txt
```

Depois, em `A`:

```text
send B teste-nak-1
```

Esperado:

- o destino calcula CRC divergente
- o pacote volta com `NAK`
- a origem agenda uma unica retransmissao

### T6 - Segunda falha e descarte

Ainda com a origem usando `*_err100.txt`:

```text
send B teste-drop-1
```

Esperado:

- primeiro `NAK` marca retry
- segundo `NAK` descarta a mensagem

### T7 - Remocao manual do token

Em um dos nos:

```text
drop-token
```

Esperado:

- o proximo token e descartado
- o anel para temporariamente

### T8 - Recuperacao por timeout

- aguardar alem de `token_timeout`

Esperado:

- a lider recria o token
- a circulacao volta

### T9 - Insercao manual de token

Em um dos nos:

```text
insert-token
```

Esperado:

- token extra entra no anel
- a lider detecta duplicacao e descarta o excedente

### T10 - Entrada dinamica

Com `A`, `B` e `C` estaveis e sem dado em voo, iniciar `D`:

```bash
python -m src.main --config configs/D.txt
```

Esperado:

- `D` envia `DISCOVER`
- os demais respondem `HELLO`
- o anel converge para `A -> B -> C -> D`

## 5. Coleta de evidencias

Salvar por caso:

- print da origem
- print do destino, quando existir
- `packets_<apelido>.csv`
- `ring_<apelido>.csv`

Eventos esperados nos CSVs:

- descoberta: `SEND_DISCOVER`, `RECV_DISCOVER`, `SEND_HELLO`, `RECV_HELLO`
- token: `SEND_TOKEN`, `RECV_TOKEN`, `DROP_TOKEN`
- dados: `SEND_DATA`, `RECV_DATA`, `ACK`, `NAK`, `FORWARD_DATA`

## 6. Fechamento

Um ensaio e considerado aprovado quando:

- todos os casos T1 a T10 passam
- os terminais e CSVs batem com o comportamento observado
- os 3 participantes conseguem explicar o fluxo:

```text
token -> origem envia dado -> dado circula -> destino valida CRC ->
dado retorna -> origem libera token
```
