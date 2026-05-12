function parseCSV(text) {
    const lines = text.trim().split("\n");

    const headers = lines[0]
        .split(",")
        .map(h => h.trim());

    return lines.slice(1).map(line => {
        const values = line.split(",");

        let obj = {};

        headers.forEach((header, index) => {
            obj[header] = values[index]?.trim();
        });

        return obj;
    });
}