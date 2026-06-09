const grupo = document.querySelector("#grupo");
const limite = document.querySelector("#limite");
const horas = document.querySelector("#horas");
const passo = document.querySelector("#passo");
const limiteKm = document.querySelector("#limiteKm");
const botao = document.querySelector("#botao");

const totalLista = document.querySelector("#totalLista");
const totalDict = document.querySelector("#totalDict");
const totalAlertas = document.querySelector("#totalAlertas");
const tabelaAlertas = document.querySelector("#tabelaAlertas");
const tabelaSatelites = document.querySelector("#tabelaSatelites");

function linhaVazia(tabela, texto, colunas) {
  tabela.innerHTML = `<tr><td colspan="${colunas}">${texto}</td></tr>`;
}

function renderizarSatelites(satelites) {
  if (satelites.length === 0) {
    linhaVazia(tabelaSatelites, "Nenhum satélite carregado.", 4);
    return;
  }

  tabelaSatelites.innerHTML = satelites.map((satelite) => `
    <tr>
      <td>${satelite.norad}</td>
      <td>${satelite.nome}</td>
      <td>${satelite.perigeu_km} km</td>
      <td>${satelite.apogeu_km} km</td>
    </tr>
  `).join("");
}

function renderizarAlertas(alertas) {
  if (alertas.length === 0) {
    linhaVazia(tabelaAlertas, "Nenhum alerta encontrado com esses parâmetros.", 5);
    return;
  }

  tabelaAlertas.innerHTML = alertas.map((alerta) => `
    <tr>
      <td><span class="risco ${alerta.risco}">${alerta.risco}</span></td>
      <td>${alerta.satelite_a}<br><small>NORAD ${alerta.norad_a}</small></td>
      <td>${alerta.satelite_b}<br><small>NORAD ${alerta.norad_b}</small></td>
      <td>${alerta.distancia} km</td>
      <td>${alerta.momento}</td>
    </tr>
  `).join("");
}

async function analisar() {
  botao.disabled = true;
  botao.textContent = "Analisando...";

  try {
    const parametros = new URLSearchParams({
      grupo: grupo.value,
      limite: limite.value,
      horas: horas.value,
      passo: passo.value,
      limite_km: limiteKm.value,
    });

    const resposta = await fetch(`/api/analisar?${parametros}`);
    const dados = await resposta.json();

    if (!resposta.ok) {
      throw new Error(dados.erro || "Erro ao analisar dados.");
    }

    totalLista.textContent = dados.quantidade_satelites;
    totalDict.textContent = dados.quantidade_no_dicionario;
    totalAlertas.textContent = dados.alertas.length;
    renderizarSatelites(dados.satelites);
    renderizarAlertas(dados.alertas);
  } catch (erro) {
    linhaVazia(tabelaAlertas, erro.message, 5);
  } finally {
    botao.disabled = false;
    botao.textContent = "Analisar";
  }
}

botao.addEventListener("click", analisar);
analisar();
