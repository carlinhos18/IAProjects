const predictionsList = [];

fetch("../datasets/ranking.csv")
    .then(response => response.text())
    .then(csv => {
        const teams = parseCSV(csv)
            .sort((a, b) => parseFloat(b.percentagem_vitorias) - parseFloat(a.percentagem_vitorias));

        const tbody = document.querySelector("#predictionsTable tbody");

        // populate team selectors
        const selectA = document.querySelector("#teamA");
        const selectB = document.querySelector("#teamB");

        teams.forEach(t => {
            const optA = document.createElement("option");
            optA.value = t.equipa;
            optA.textContent = t.equipa;
            selectA.appendChild(optA);

            const optB = document.createElement("option");
            optB.value = t.equipa;
            optB.textContent = t.equipa;
            selectB.appendChild(optB);
        });

        function computeAndShow(aName, bName) {
            const a = teams.find(x => x.equipa === aName);
            const b = teams.find(x => x.equipa === bName);
            const out = document.querySelector('#matchResult');

            if (!a || !b) {
                out.textContent = '';
                return;
            }

            if (a.equipa === b.equipa) {
                out.innerHTML = '<strong>Mesma equipa escolhida.</strong>';
                return;
            }

            const pA = parseFloat(a.percentagem_vitorias) || 0;
            const pB = parseFloat(b.percentagem_vitorias) || 0;
            const total = pA + pB || 1;
            const normA = ((pA / total) * 100).toFixed(1);
            const normB = ((pB / total) * 100).toFixed(1);
            const fav = pA >= pB ? a.equipa : b.equipa;

            out.innerHTML = `
                <strong>${a.equipa} vs ${b.equipa}</strong><br>
                Probabilidade ${a.equipa}: ${normA}% — ${b.equipa}: ${normB}%<br>
                Favorito: <em>${fav}</em>
            `;
        }

        selectA.addEventListener('change', () => computeAndShow(selectA.value, selectB.value));
        selectB.addEventListener('change', () => computeAndShow(selectA.value, selectB.value));

        // pre-select first two distinct teams
        if (teams.length >= 2) {
            selectA.selectedIndex = 0;
            selectB.selectedIndex = 1;
            computeAndShow(selectA.value, selectB.value);
        }

        const comparisonResults = document.querySelector('#comparisonResults');

        const loadSampleBtn = document.querySelector('#loadSample');

        function tryAutoCompare() {
            if (!predictionsList.length) return;
            fetch('../datasets/actuals.csv')
                .then(r => {
                    if (!r.ok) throw new Error('no actuals');
                    return r.text();
                })
                .then(text => compareActuals(text))
                .catch(() => {
                    // no sample actuals available; ignore
                });
        }

        if (loadSampleBtn) {
            loadSampleBtn.addEventListener('click', () => {
                fetch('../datasets/actuals.csv')
                    .then(r => r.text())
                    .then(text => compareActuals(text))
                    .catch(() => {
                        if (comparisonResults) comparisonResults.textContent = 'Não foi possível carregar sample actuals.';
                    });
            });
        }

        function pushPrediction(home, away, pHome, pAway, fav) {
            predictionsList.push({ home, away, pHome, pAway, predictedWinner: fav });
        }

        // try to load a dedicated predictions CSV; otherwise fallback to matches.csv and compute
        fetch('../datasets/predictions.csv')
            .then(r => {
                if (!r.ok) throw new Error('no predictions csv');
                return r.text();
            })
            .then(text => {
                const rows = parseCSV(text);
                rows.forEach(row => {
                    const home = row.equipa1 || '';
                    const away = row.equipa2 || '';
                    const p1 = row.prob_equipa1 || row.prob1 || '';
                    const p2 = row.prob_equipa2 || row.prob2 || '';
                    const fav = row.favorito || '';

                    tbody.innerHTML += `
                        <tr>
                            <td>${row.jogo || (home + ' vs ' + away)}</td>
                            <td>${p1}</td>
                            <td>${p2}</td>
                            <td>${fav}</td>
                        </tr>
                    `;

                    pushPrediction(home, away, p1, p2, fav);
                });
                // auto-run comparison if sample actuals exist
                tryAutoCompare();
            })
            .catch(() => {
                // fallback: use matches.csv and ranking-derived probabilities
                fetch('../datasets/matches.csv')
                    .then(rr => rr.text())
                    .then(text => {
                        const matches = parseCSV(text);
                        matches.forEach(m => {
                            const a = teams.find(t => t.equipa === m.equipa_casa);
                            const b = teams.find(t => t.equipa === m.equipa_fora);
                            const pA = a ? parseFloat(a.percentagem_vitorias) : 0;
                            const pB = b ? parseFloat(b.percentagem_vitorias) : 0;
                            const total = pA + pB || 1;
                            const normA = ((pA / total) * 100).toFixed(1);
                            const normB = ((pB / total) * 100).toFixed(1);
                            const fav = pA >= pB ? (a ? a.equipa : m.equipa_casa) : (b ? b.equipa : m.equipa_fora);

                            tbody.innerHTML += `
                                <tr>
                                    <td>${m.equipa_casa} vs ${m.equipa_fora}</td>
                                    <td>${normA}%</td>
                                    <td>${normB}%</td>
                                    <td>${fav}</td>
                                </tr>
                            `;

                            pushPrediction(m.equipa_casa, m.equipa_fora, normA, normB, fav);
                        });
                        // auto-run comparison if sample actuals exist
                        tryAutoCompare();
                    })
                    .catch(() => {
                        tbody.innerHTML = `
                            <tr>
                                <td colspan="4">Nenhuma previsão disponível.</td>
                            </tr>
                        `;
                    });
            });

        // wire file input for actuals comparison
        const actualsInput = document.querySelector('#actualsFile');
        if (actualsInput) {
            actualsInput.addEventListener('change', e => {
                const file = e.target.files[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = () => compareActuals(reader.result);
                reader.readAsText(file);
            });
        }

        let lastMismatches = [];

        function compareActuals(text) {
            const actuals = parseCSV(text);
            let total = 0;
            let correct = 0;
            const mismatches = [];
            const teamStats = {};

            actuals.forEach(act => {
                // find prediction by matching home/away
                const match = predictionsList.find(p => (p.home === act.equipa_casa && p.away === act.equipa_fora) || (p.home === act.equipa_fora && p.away === act.equipa_casa));
                if (!match) return;
                total += 1;
                const actualWinner = act.vencedor || (parseInt(act.sets_casa) > parseInt(act.sets_fora) ? act.equipa_casa : act.equipa_fora);
                if (!actualWinner) return;
                const predicted = match.predictedWinner;
                if (predicted === actualWinner) {
                    correct += 1;
                } else {
                    mismatches.push({ home: match.home, away: match.away, predicted, actual: actualWinner });
                }
            });

            // compute per-team stats (for matches with predictions)
            actuals.forEach(act => {
                const match = predictionsList.find(p => (p.home === act.equipa_casa && p.away === act.equipa_fora) || (p.home === act.equipa_fora && p.away === act.equipa_casa));
                if (!match) return;
                const actualWinner = act.vencedor || (parseInt(act.sets_casa) > parseInt(act.sets_fora) ? act.equipa_casa : act.equipa_fora);
                if (!actualWinner) return;

                const teamsInMatch = [act.equipa_casa, act.equipa_fora];
                teamsInMatch.forEach(name => {
                    if (!teamStats[name]) teamStats[name] = { played: 0, correct: 0 };
                    teamStats[name].played += 1;
                });

                const predicted = match.predictedWinner;
                if (predicted === actualWinner) {
                    // mark both teams as correct for that match (model predicted winner correctly)
                    teamStats[act.equipa_casa].correct += 1;
                    teamStats[act.equipa_fora].correct += 1;
                }
            });

            const accuracy = total ? ((correct / total) * 100).toFixed(1) : 'N/A';
            if (comparisonResults) {
                comparisonResults.innerHTML = `
                    <strong>Total de jogos comparados:</strong> ${total}<br>
                    <strong>Acertos:</strong> ${correct}<br>
                    <strong>Acurácia:</strong> ${accuracy === 'N/A' ? accuracy : accuracy + '%'}
                `;

                if (mismatches.length) {
                    comparisonResults.innerHTML += '<h3>Erros</h3>';
                    comparisonResults.innerHTML += '<ul>' + mismatches.map(mm => `<li>${mm.home} vs ${mm.away} — previsto: ${mm.predicted} / real: ${mm.actual}</li>`).join('') + '</ul>';
                }
                // populate per-team stats table
                const teamTbody = document.querySelector('#teamStatsTable tbody');
                if (teamTbody) {
                    teamTbody.innerHTML = '';
                    // sort teams by played desc
                    Object.keys(teamStats).sort((a,b) => (teamStats[b].played - teamStats[a].played)).forEach(name => {
                        const s = teamStats[name];
                        const acc = s.played ? ((s.correct / s.played) * 100).toFixed(1) + '%' : 'N/A';
                        teamTbody.innerHTML += `<tr><td>${name}</td><td>${s.played}</td><td>${s.correct}</td><td>${acc}</td></tr>`;
                    });
                }
                lastMismatches = mismatches;
            }
            // enable download button if mismatches exist
            const downloadBtn = document.querySelector('#downloadMismatches');
            if (downloadBtn) downloadBtn.disabled = lastMismatches.length === 0;
        }

        // download mismatches csv
        const downloadBtn = document.querySelector('#downloadMismatches');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                if (!lastMismatches || !lastMismatches.length) return;
                const header = 'home,away,predicted,actual\n';
                const rows = lastMismatches.map(m => `${m.home},${m.away},${m.predicted},${m.actual}`).join('\n');
                const blob = new Blob([header + rows], { type: 'text/csv' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'mismatches.csv';
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(url);
            });
            downloadBtn.disabled = true;
        }
    })
    .catch(() => {
        const tbody = document.querySelector("#predictionsTable tbody");
        tbody.innerHTML = `
            <tr>
                <td colspan="4">Erro ao carregar as previsões.</td>
            </tr>
        `;
    });