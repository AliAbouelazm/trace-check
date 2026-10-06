import {readFileSync} from 'node:fs';
import {analyzeRun} from '../web/core.js';
const runs=JSON.parse(readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(runs.map(run=>analyzeRun(run))));
