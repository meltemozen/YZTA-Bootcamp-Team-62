import { copyFile, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const packageEntry = fileURLToPath(import.meta.resolve('turkey-neighbourhoods'));
const packageRoot = resolve(dirname(packageEntry), '..');
const destination = resolve(import.meta.dirname, '..', 'src', 'data');

await mkdir(destination, { recursive: true });
await Promise.all([
  copyFile(
    resolve(packageRoot, 'src', 'data', 'cityList.json'),
    resolve(destination, 'turkey-provinces.json')
  ),
  copyFile(
    resolve(packageRoot, 'src', 'data', 'districtsByCityCode.json'),
    resolve(destination, 'turkey-districts.json')
  ),
]);

console.log('Türkiye il/ilçe verisi turkey-neighbourhoods paketinden güncellendi.');
