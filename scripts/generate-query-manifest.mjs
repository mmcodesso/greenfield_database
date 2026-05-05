import { promises as fs } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");
const queriesRoot = path.join(repoRoot, "queries");
const outputPath = path.join(repoRoot, "src", "generated", "queryManifest.js");

async function listSqlFiles(directory) {
  const entries = await fs.readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map(async (entry) => {
      const fullPath = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        return listSqlFiles(fullPath);
      }
      if (entry.isFile() && entry.name.endsWith(".sql")) {
        return [fullPath];
      }
      return [];
    })
  );
  return nested.flat();
}

function extractHeaderValue(sql, labels) {
  const labelPattern = labels
    .map((label) => label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("|");
  const match = sql.match(new RegExp(`^--\\s*(?:${labelPattern}):\\s*(.+)$`, "im"));
  return match ? match[1].trim() : undefined;
}

function parseTeachingMetadata(sql) {
  return {
    teachingObjective: extractHeaderValue(sql, ["Teaching objective"]),
    mainTables: extractHeaderValue(sql, ["Main tables"]),
    outputShape: extractHeaderValue(sql, ["Output shape", "Expected output shape"]),
  };
}

async function main() {
  const files = await listSqlFiles(queriesRoot);
  const manifestEntries = await Promise.all(
    files
      .sort()
      .map(async (fullPath) => {
        const relativePath = path.relative(queriesRoot, fullPath).split(path.sep).join("/");
        const [category] = relativePath.split("/");
        const sql = await fs.readFile(fullPath, "utf8");
        return [
          relativePath,
          {
            category,
            filename: path.basename(relativePath),
            publicPath: `/${relativePath}`,
            ...parseTeachingMetadata(sql),
          },
        ];
      })
  );
  const manifest = Object.fromEntries(manifestEntries);

  const output = `const queryManifest = ${JSON.stringify(manifest, null, 2)};\n\nexport default queryManifest;\n`;
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, output, "utf8");
  console.log(`Wrote ${outputPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
