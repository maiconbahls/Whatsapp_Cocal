# WhatsApp Massa

Este aplicativo permite enviar mensagens personalizadas em massa via WhatsApp Web utilizando uma planilha Excel como base de dados.

## Requisitos

- Python 3.8 ou superior
- Navegador Google Chrome instalado
- Conta no WhatsApp conectada ao WhatsApp Web

## Instalação

1. Clone ou baixe este repositório
2. Abra um terminal na pasta do projeto
3. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Como Usar

1. Certifique-se de que o arquivo `contatos.xlsx` está na mesma pasta do aplicativo ou prepare seu próprio arquivo Excel.
   - O arquivo deve ter as colunas: `Nome`, `Telefone`, `texto`.
2. Execute o aplicativo:

```bash
streamlit run app.py
```

3. O navegador será aberto com a interface do aplicativo.
4. **IMPORTANTE**: Abra o WhatsApp Web (web.whatsapp.com) em outra aba e faça login com seu celular ANTES de iniciar o envio.
5. Clique em "Enviar Mensagens para Todos" e aguarde. 
   - **Não utilize o computador enquanto o envio estiver em progresso**, pois a automação controla o mouse e teclado.

## Observações

- O intervalo entre mensagens é configurável para evitar bloqueios do WhatsApp.
- Recomenda-se começar com poucos contatos para testar.
