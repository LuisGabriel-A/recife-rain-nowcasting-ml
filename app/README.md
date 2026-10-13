# AlertaChuva Recife

Aplicativo web instalável (PWA) para apresentar **avisos simples de chuva forte
para famílias de Recife**. A tela principal não exige cadastro, senha ou medições
digitadas pelo cidadão. O laboratório técnico anterior continua em `/laboratorio`.

## Executar no computador

Com Python 3.14.6, ambiente validado e os seis artefatos locais existentes:

```powershell
python -m pip install -r requirements-webpush.txt
python -m src.check_environment --webpush
python -m pip check
python -m app.server --port 8000
```

Neste computador, o ambiente preparado é `.venv-repro`:

```powershell
& .\.venv-repro\Scripts\python.exe -m app.server --port 8000
```

Abra [AlertaChuva Recife](http://127.0.0.1:8000). Ctrl+C encerra o servidor.
`--port`, `--model-dir` e `--push-contact` são opções do operador.
O servidor permanece em 127.0.0.1; não publica o site na internet. Artefatos
ausentes/incompatíveis geram erro explícito, sem treinamento automático.

Sem os pacotes opcionais de push, `requirements.txt` permite consultar previsões;
a configuração HTTP informa que as notificações estão indisponíveis.

## Dados de hoje: importação do operador

1. Abra a [tabela oficial da A301](https://tempo.inmet.gov.br/TabelaEstacoes/A301).
2. Confirme **Recife / A301** e selecione um período contendo ao menos sete horas
   consecutivas recentes. Baixe usando **Baixar CSV**.
3. Importe o arquivo, confirmando explicitamente a estação:

```powershell
python -m src.data.inmet_recent "C:\caminho\observacoes-inmet.csv" --station A301
```

O CSV oficial possui Data, Hora (UTC), Temp. Ins. (C), Umi. Ins. (%),
Pressao Ins. (hPa) e Chuva (mm), separados por ponto e vírgula. Decimais com
vírgula são convertidos; ausência e sentinelas 9999 permanecem ausentes.
A pressão de estação em hPa corresponde à unidade mb usada pelos modelos.
O CSV não contém código da estação: a confirmação do operador é registrada,
junto da URL, hash SHA-256 e horário da importação.

Somente as últimas sete horas necessárias ficam no estado privado
`app/.state/observations.json`. Linhas finais totalmente vazias da tabela são
tratadas como horários ainda sem medição; uma última medição parcial bloqueia
a janela, sem recorrer silenciosamente a uma hora completa anterior.
Lacunas, duplicatas, valores inválidos e observações futuras são rejeitados.
Dados ausentes nunca viram chuva zero.

A página e o monitor consultam esse estado a cada 60 segundos. O cidadão não
faz a importação. A integração automática contínua precisa de acesso autorizado
à fonte: o endpoint legado retornou 204 na consulta, enquanto a tabela usa uma
interface protegida com reCAPTCHA. Nenhum token/proteção foi contornado.

O limite de atualização é **duas horas desde a última observação**. Esta é uma
regra operacional da aplicação, sem alteração dos thresholds científicos.
Previsões continuam referidas a t+1h até t+6h; horários já encerrados ficam
inativos. Fonte antiga/futura/incompleta produz **Previsão indisponível agora**.

## Avisos no aparelho

O botão **Receber avisos** prepara o service worker e pede permissão apenas
após a ação do usuário. A inscrição real usa PushManager, chave pública VAPID
e armazenamento privado no backend. **Ajustes** permite desativar a inscrição
ou mostrar um teste local claramente identificado.

O monitor envia somente decisões positivas de horizontes futuros com observações
recentes. A entrega usa Web Push criptografado (aes128gcm) e assinatura VAPID.
O horário previsto identifica o evento para evitar repetições. TTL/expiração são
limitados pela validade da previsão e da observação; inscrições 404/410 são removidas.
A chave VAPID persiste para não invalidar inscrições a cada reinício.

`app/.state/vapid_private.pem` e `subscriptions.sqlite3` são privados e ignorados
pelo Git, assim como as observações. Não são expostos pelo servidor. O contato
VAPID padrão é a URL real do repositório; o operador pode informar outra URL HTTPS
com `--push-contact`. Não publique backups desse estado.

Para o celular, o site precisa estar **publicado em HTTPS** com o backend ativo
e conectado. No iPhone compatível com Web Push, adicione à tela inicial e abra
por lá. O endereço localhost funciona apenas neste computador. Hospedagem,
entrega real em Android/iPhone e operação contínua estão pendentes.
O botão de teste verifica a exibição local; não prova entrega remota.

## Tela e demonstração

A página apresenta atenção, sem indicação ou indisponível, seis horários no fuso
de Recife e medições atuais separadas da previsão. Não mostra scores como
percentuais de chance, nem inventa quantidade de chuva/temperatura previstas.
Sem indicação não significa segurança ou ausência de chuva. A estação única
não fornece previsão específica por bairro ou risco de enchente/deslizamento.

**Ver demonstração** mostra uma janela histórica com data original e faixa
visível dizendo que não é previsão de hoje. Esse fluxo nunca dispara push de chuva.
**Voltar para agora** consulta novamente a fonte recente. Exemplos históricos
dependem do dataset local; se ele não existir, a demonstração informa indisponibilidade.

O service worker guarda somente o layout estático. Previsões/inscrições não entram
no cache offline. Sem conexão, a interface remove a indicação atual e apresenta
indisponibilidade. Mensagens incluem texto além de cor, botões grandes, foco
visível e aviso de estado acessível.

## HTTP

| Método/rota | Uso |
|---|---|
| GET / | Aplicativo para cidadãos |
| GET /api/status | Aviso atual e horários, sem scores/thresholds |
| GET /api/demo/0 ou /1 | Exemplos históricos isolados do push |
| GET /api/push/config | Disponibilidade e chave VAPID pública |
| POST /api/push/subscribe | Inscrição voluntária do navegador |
| POST /api/push/unsubscribe | Revogação da inscrição |
| GET /manifest.webmanifest e /sw.js | Instalação e recebimento em segundo plano |
| GET /laboratorio | Interface técnica anterior |
| GET /api/health e /api/examples | Saúde/modelos e exemplos técnicos |
| POST /api/predict | Contrato técnico preservado: observations ou features |

Corpos JSON têm limite de 65.536 bytes. Campos duplicados/NaN são recusados.
Origens de outro domínio são recusadas. Inscrições exigem chaves criptográficas
válidas e provedores HTTPS permitidos; redirects e DNS privado são bloqueados.
Os arquivos expostos são uma lista fixa de assets, sem acesso ao workspace.

## Validação e próximos passos

```powershell
python -m unittest discover -s tests -v
node --test tests/test_service_worker.cjs
python -m src.check_environment --webpush
python -m pip check
```

Node é necessário somente para verificar JavaScript, sem dependências npm.
Os testes de push usam entrega HTTP simulada e criptografia real; não inscrevem
pessoas nem enviam avisos reais. Testes com os joblibs são somente de leitura.
A geração dos ícones (`python app/build_icons.py`) requer Pillow apenas no
ambiente de criação dos assets; as imagens prontas são versionáveis.

Consulte [alinhamento do produto](../docs/PRODUCT_ALIGNMENT.md),
[arquitetura](../docs/architecture.md) e
[registro das verificações](../docs/validation/citizen_app_checks.json).
Faltam fonte automática autorizada, hospedagem HTTPS, teste real do push,
validação prospectiva e avaliação com o público. Os seis modelos, as 20 features
e os resultados científicos permanecem congelados.
