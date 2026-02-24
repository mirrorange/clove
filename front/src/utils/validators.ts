/**
 * Validates if a string is a valid UUID
 * @param uuid - The string to validate
 * @returns boolean indicating if the string is a valid UUID
 */
export function isValidUUID(uuid: string): boolean {
    const generalUuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

    return generalUuidRegex.test(uuid)
}

/**
 * Formats a UUID string to lowercase with dashes
 * @param uuid - The UUID string to format
 * @returns The formatted UUID string or the original if invalid
 */
export function formatUUID(uuid: string): string {
    const cleaned = uuid.trim().toLowerCase()

    if (isValidUUID(cleaned)) {
        return cleaned
    }

    // Try to format if it's 32 hex characters without dashes
    const hexOnly = cleaned.replace(/[^0-9a-f]/gi, '')
    if (hexOnly.length === 32) {
        return `${hexOnly.slice(0, 8)}-${hexOnly.slice(8, 12)}-${hexOnly.slice(12, 16)}-${hexOnly.slice(
            16,
            20,
        )}-${hexOnly.slice(20, 32)}`
    }

    return uuid
}
