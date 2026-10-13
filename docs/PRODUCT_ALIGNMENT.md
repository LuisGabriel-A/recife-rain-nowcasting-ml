# AlertaChuva Recife — adaptação ao objetivo do produto

Referência: `AlertaChuva.pdf`, apresentação fornecida pelo usuário, especialmente
as páginas 19–23 (identidade azul/branca, acesso simples, previsão e avisos).
O usuário confirmou que não existe código React Native/Expo nem projeto Firebase.
Esta implementação aproveita o backend Python e entrega uma PWA, que pode ser
adicionada à tela inicial, sem criar outra base de código ou exigir uma conta.

## Público e uso

Famílias de Recife, especialmente pessoas em situação de risco e com pouca
familiaridade com tecnologia. A jornada principal é abrir, ler o aviso e optar
por receber notificações. Nenhum formulário de medições, JSON, senha, endereço
ou localização aparece nessa jornada. O laboratório continua disponível para
pesquisadores em `/laboratorio`.

| Elemento da referência | Implementação atual |
|---|---|
| AlertaChuva Recife, azul e branco | Identidade, ícone de nuvem/chuva e tela responsiva |
| Entrada/cadastro | Acesso direto sem cadastro, adequado à simplicidade solicitada |
| Aviso de chuva forte e horários | Decisões dos seis modelos existentes, no horário de Recife |
| Temperatura/chuva no protótipo | Apenas medições observadas; os modelos não preveem quantidade ou temperatura |
| Push simples | Inscrição voluntária, Web Push criptografado, revogação e monitor |
| Bairro | Sem previsão por bairro: a evidência disponível é de uma única estação |
| React Native/Expo/Firebase | Não havia projeto existente; PWA com backend atual e padrão Web Push |

As menções a vento/períodos da apresentação não substituem a metodologia
revalidada: A301, período efetivo 2018–2021, 20 features sem vento, seis thresholds
congelados e ausência de imputação. K-Means permanece análise descritiva.

## O que foi validado e o que falta

A importação oficial com conversão de unidade/formato, a inferência atual, os
estados sem indicação/atenção/indisponível e a demonstração histórica funcionam
localmente. O aviso sem indicação não promete ausência de chuva ou segurança.
O modelo detecta a definição operacional do projeto (≥10 mm/h), sem estimar
enchentes, deslizamentos ou um risco individual de cada família.

O envio push tem criptografia/VAPID, chave persistente, inscrições revogáveis,
deduplicação por horário previsto e expiração. O monitor consulta observações
importadas a cada 60 segundos. Demonstrações, horários encerrados e fontes
desatualizadas não geram avisos de chuva. O teste no menu verifica a exibição
local; ele não demonstra entrega remota com o aplicativo fechado.

Em 13/10/2026, a tabela oficial da A301 disponibilizou medições atuais e um CSV
foi baixado pela interface oficial. O endpoint legado consultado retornou HTTP
204; o portal usa uma interface protegida com reCAPTCHA. Não se contornou essa
proteção. O CSV não contém código da estação: o operador confirma a tabela A301,
e o importador registra essa confirmação, URL, hash e data de acesso.

Para o uso contínuo por famílias, ainda são necessários:

1. Acesso autorizado e confiável à fonte recente do INMET para coleta automática.
2. Hospedagem HTTPS com processo persistente, estado privado protegido e gestão
   operacional das inscrições; o servidor atual fica restrito ao localhost.
3. Teste de inscrição/entrega/revogação em Android e iPhone, inclusive aplicativo
   fechado. No iPhone, a instalação na tela inicial é necessária para Web Push.
4. Avaliação prospectiva dos modelos congelados com observações recentes, sem
   ajustar modelos/thresholds ou declarar desempenho operacional a partir da UI.
5. Testes de compreensão e acessibilidade com o público pretendido.

## Fontes técnicas

- [Tabela oficial da A301](https://tempo.inmet.gov.br/TabelaEstacoes/A301).
- [Orientações de acesso do INMET](https://portal.inmet.gov.br/noticias/saiba-como-acessar-os-dados-meteorol%C3%B3gicos-dispon%C3%ADveis-no-site-do-inmet).
- [Implementação pywebpush](https://github.com/web-push-libs/pywebpush).
- [Apple: Web Push](https://developer.apple.com/documentation/usernotifications/sending-web-push-notifications-in-web-apps-and-browsers).
- [MDN: operação offline e em segundo plano](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Offline_and_background_operation).

O PDF acadêmico de 27 páginas continua preservado como versão documental
anterior desta interface. Nenhum resultado científico foi reescrito.
