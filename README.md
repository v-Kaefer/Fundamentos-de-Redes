# Token Ring UDP

Simulador de rede em anel com passagem de token, usando UDP e biblioteca
padrao do Python.

## Requisitos

- Python 3.11+
- 1 ou mais maquinas na mesma rede
- UDP liberado no firewall

## Estrutura

```text
src/      codigo da aplicacao
configs/  perfis de execucao
tests/    testes unitarios
logs/     CSVs gerados por no
```

## Execucao local

Suba uma instancia por terminal:

```bash
python -m src.main --config configs/A.txt
python -m src.main --config configs/B.txt
python -m src.main --config configs/C.txt
```

Comandos da interface:

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

## Testes unitarios

```bash
python -m unittest discover -s tests -v
```

## Testes reais

O roteiro completo esta em [REAL_TESTS.md](E:/Trabalhos-Redes/Fundamentos-Marcelo/REAL_TESTS.md).

Antes de subir cada maquina, rode:

```bash
python scripts/preflight_check.py --config configs/A.txt
```

Para forcar erro na origem durante o teste de `NAK`, use um perfil `*_err100.txt`.

## Configs disponiveis

- `A.txt`, `B.txt`, `C.txt`, `D.txt`: operacao normal
- `A_err100.txt`, `B_err100.txt`, `C_err100.txt`, `D_err100.txt`: erro 100%
