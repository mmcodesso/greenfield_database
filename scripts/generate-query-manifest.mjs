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

async function main() {
  const files = await listSqlFiles(queriesRoot);
  const manifest = Object.fromEntries(
    files
      .sort()
      .map((fullPath) => {
        const relativePath = path.relative(queriesRoot, fullPath).split(path.sep).join("/");
        const [category] = relativePath.split("/");
        return [
          relativePath,
          {
            category,
            filename: path.basename(relativePath),
            publicPath: `/${relativePath}`,
          },
        ];
      })
  );

  const output = `const queryManifest = ${JSON.stringify(manifest, null, 2)};\n\nexport default queryManifest;\n`;
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, output, "utf8");
  console.log(`Wrote ${outputPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
