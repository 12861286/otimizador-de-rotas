# 🚚 Router Master Pro — GMPRO

Roteirizador inteligente para até **100 paradas**, com dois motores de otimização:

- **Algoritmo Local** (gratuito, sem API): Nearest Neighbor + 2-opt. Funciona offline.
- **Google Fleet Routing** (com credenciais GCP): API oficial do Google para otimização de frota.

---

## 🚀 Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## ☁️ Deploy no Streamlit Cloud

1. Suba este repositório no GitHub
2. Acesse [share.streamlit.io](https://share.streamlit.io)
3. Conecte o repositório e aponte para `app.py`
4. Pronto!

---

## 📋 Formato da planilha

Sua planilha precisa ter obrigatoriamente:

| Coluna | Tipo | Exemplo |
|--------|------|---------|
| `Latitude` | float | -19.9245 |
| `Longitude` | float | -43.9352 |
| `Nome` | texto *(opcional)* | Cliente A |

> A **primeira linha** da planilha será o ponto de partida da rota.

---

## 🔑 Como configurar o Google Fleet Routing

1. No [Google Cloud Console](https://console.cloud.google.com), acesse seu projeto
2. Ative a API **Cloud Optimization API**
3. Vá em **IAM & Admin → Service Accounts**
4. Crie uma conta de serviço com papel `Cloud Optimization Admin`
5. Gere e baixe a chave em formato **JSON**
6. No app, selecione "Google Fleet Routing" e faça upload do JSON

> Sem o JSON, o app usa automaticamente o algoritmo local como fallback.

---

## 🧠 Como funciona o Algoritmo Local

1. **Nearest Neighbor**: Começa no depósito e sempre vai para a parada mais próxima não visitada
2. **2-opt**: Melhora a rota trocando pares de arestas que se cruzam (até 500 iterações)

Para 100 paradas, o resultado é tipicamente **15–25% melhor** que uma rota aleatória.
