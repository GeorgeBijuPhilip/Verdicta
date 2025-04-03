export const formatTextWithBreaks = (text: string): string => {
    return text
        .replace(/<br><br>/g, '\n\n')  // Replace double breaks first
        .replace(/<br>/g, '\n');        // Then handle single breaks
};