import React from 'react';
import { formatTextWithBreaks } from '../utils/textFormatting';

interface FormattedTextProps {
    text: string;
}

const FormattedText: React.FC<FormattedTextProps> = ({ text }) => {
    const formattedText = formatTextWithBreaks(text);
    
    return (
        <div style={{ 
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word'
        }}>
            {formattedText}
        </div>
    );
};

export default FormattedText;
