fetch("../datasets/matches.csv")
    .then(response => response.text())
    .then(csv => {

        const matches = parseCSV(csv);

        const tbody = document.querySelector("#matchesTable tbody");

        matches.forEach(match => {

            tbody.innerHTML += `
                <tr>
                    <td>${match.data}</td>
                    <td>${match.equipa_casa}</td>
                    <td>${match.equipa_fora}</td>
                    <td>${match.sets_casa} - ${match.sets_fora}</td>
                    <td>${match.vencedor}</td>
                </tr>
            `;
        });
    })
    .catch(() => {
        const tbody = document.querySelector("#matchesTable tbody");
        tbody.innerHTML = `
            <tr>
                <td colspan="5">Erro ao carregar os jogos.</td>
            </tr>
        `;
    });