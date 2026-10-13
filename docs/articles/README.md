# Artigo técnico do projeto

Este diretório reúne os arquivos do artigo acadêmico sobre a metodologia,
os resultados corrigidos e o desenvolvimento da aplicação Recife Rain Nowcasting.

- [Abrir ou baixar o artigo em PDF (27 páginas)](artigo_recife_rain_nowcasting.pdf)
- [Ler a versão editável em Markdown](artigo_recife_rain_nowcasting.md)
- [Consultar as verificações e comandos de geração](validacao_artigo.json)

O artigo é uma versão documental de 13/10/2026. Distingue resultados científicos
vigentes, histórico experimental e funcionalidades implementadas. Também explica
os próximos passos para conectar o aplicativo a observações atuais do INMET.
Autoria formal, proveniência dos arquivos originais e termos de uso/licença
continuam pendentes antes de uma submissão acadêmica.

## Fontes e geração

O [texto-fonte](../artigo_recife_rain_nowcasting.md) contém marcadores para tabelas.
O [gerador](../build_article.py) resolve esses marcadores usando os CSVs corrigidos
e as configurações congeladas, produzindo PDF, Markdown completo e registro de
validação neste diretório.

```powershell
python docs/build_article.py
```

A geração requer um ambiente documental separado com `reportlab` e `pypdf`,
além das fontes Arial e Times New Roman em `C:/Windows/Fonts`. Essas dependências
não integram o ambiente de inferência validado. Os metadados dos modelos precisam
estar disponíveis localmente; o gerador não ajusta modelos nem executa seleção.
Após regenerar, renderize e revise as páginas: o registro inicia com revisão
visual pendente. A edição disponível neste diretório já foi revisada.

O PDF foi transferido de `output/pdf/` para esta pasta sem alterar seus bytes,
para ficar acessível na documentação e no GitHub. Dados brutos/processados,
joblibs, ambientes virtuais e logs locais continuam fora do versionamento.
