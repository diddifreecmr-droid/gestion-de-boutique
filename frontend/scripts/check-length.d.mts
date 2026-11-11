export const MAX_LINES: number;
export function countLines(text: string): number;
export function sourceFiles(dir: string): Generator<string>;
export function findTooLong(dirs: string[], max?: number): { file: string; lines: number }[];
