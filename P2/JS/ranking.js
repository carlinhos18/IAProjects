fetch("../datasets/ranking.csv")
    .then(response => response.text())
    .then(csv => {

        const teams = parseCSV(csv);

        teams.sort((a, b) =>
            parseFloat(b.percentagem_vitorias) -
            parseFloat(a.percentagem_vitorias)
        );

        const tbody = document.querySelector("#rankingTable tbody");

        teams.forEach((team, index) => {

            tbody.innerHTML += `
                <tr>
                    <td>${index + 1}</td>
                    <td>${team.equipa}</td>
                    <td>${team.vitorias}</td>
                    <td>${team.derrotas}</td>
                    <td>${team.saldo_pontos}</td>
                    <td>${(team.percentagem_vitorias * 100)}%</td>
                </tr>
            `;
        });
    })
    .catch(() => {
        const tbody = document.querySelector("#rankingTable tbody");
        tbody.innerHTML = `
            <tr>
                <td colspan="6">Erro ao carregar o ranking.</td>
            </tr>
        `;
    });