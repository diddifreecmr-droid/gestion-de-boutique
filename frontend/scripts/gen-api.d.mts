export const CONTRACT: string;
export const OUTPUT: string;
export function generateSchema(contract?: string): Promise<string>;
export function isUpToDate(contract?: string, output?: string): Promise<boolean>;
