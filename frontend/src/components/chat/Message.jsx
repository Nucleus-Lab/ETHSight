import React from 'react';
import PropTypes from 'prop-types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const Message = ({ text, isUser, timestamp, isError, isTyping }) => {
  // Function to highlight visualization mentions in the message
  const highlightMentions = (text) => {
    if (!text) return '';
    
    // First highlight @fig: mentions
    let highlightedText = text.replace(
      /@\s*fig:(\d+)/g, 
      '<span class="inline-flex items-center px-2 py-0.5 rounded text-sm font-medium bg-blue-100 text-blue-800">@fig:$1</span>'
    );
    
    // Then highlight @signal: mentions with the same styling
    highlightedText = highlightedText.replace(
      /@\s*signal:(\d+)/g,
      '<span class="inline-flex items-center px-2 py-0.5 rounded text-sm font-medium bg-blue-100 text-blue-800">@signal:$1</span>'
    );
    
    return highlightedText;
  };

  // Custom components for ReactMarkdown
  const components = {
    // Style code blocks
    code: ({ node, inline, className, children, ...props }) => {
      const match = /language-(\w+)/.exec(className || '');
      return !inline && match ? (
        <div className="relative group">
          <div className="absolute -top-2 right-2 px-1.5 py-0.5 text-xs font-mono text-gray-500 bg-gray-100 rounded opacity-0 group-hover:opacity-100 transition-opacity">
            {match[1]}
          </div>
          <pre className="bg-gray-900 text-gray-100 p-2 rounded-lg my-1.5 overflow-x-auto font-mono text-xs">
            <code className={className} {...props}>
              {children}
            </code>
          </pre>
        </div>
      ) : (
        <code className="px-1 py-0.5 bg-gray-100 text-gray-800 rounded font-mono text-xs" {...props}>
          {children}
        </code>
      );
    },
    // Style links
    a: ({ node, children, href, ...props }) => (
      <a 
        href={href} 
        className="text-blue-600 hover:text-blue-800 hover:underline transition-colors duration-200" 
        target="_blank" 
        rel="noopener noreferrer" 
        {...props}
      >
        {children}
      </a>
    ),
    // Style headings
    h1: ({ node, children, ...props }) => (
      <h1 className="text-xl font-bold mt-2 mb-1 text-gray-900" {...props}>{children}</h1>
    ),
    h2: ({ node, children, ...props }) => (
      <h2 className="text-lg font-bold mt-1.5 mb-1 text-gray-800" {...props}>{children}</h2>
    ),
    h3: ({ node, children, ...props }) => (
      <h3 className="text-base font-semibold mt-1.5 mb-0.5 text-gray-700" {...props}>{children}</h3>
    ),
    // Style lists
    ul: ({ node, children, ...props }) => (
      <ul className="list-disc pl-4 my-0.5 space-y-0 text-sm marker:text-gray-400" {...props}>{children}</ul>
    ),
    ol: ({ node, children, ...props }) => (
      <ol className="list-decimal pl-4 my-0.5 space-y-0 text-sm marker:text-gray-400" {...props}>{children}</ol>
    ),
    // Style list items
    li: ({ node, children, ...props }) => {
      // Check if the first child is a paragraph and remove its margin if it is
      const content = React.Children.map(children, child => {
        if (React.isValidElement(child) && child.type === 'p') {
          return React.cloneElement(child, {
            className: 'mb-0.5 text-sm'
          });
        }
        return child;
      });
      
      return (
        <li className="text-sm" {...props}>
          {content}
        </li>
      );
    },
    // Style blockquotes
    blockquote: ({ node, children, ...props }) => (
      <blockquote className="border-l-4 border-gray-300 pl-3 my-1 italic text-gray-700 bg-gray-50 py-1 rounded-r text-sm" {...props}>
        {children}
      </blockquote>
    ),
    // Style tables
    table: ({ node, children, ...props }) => (
      <div className="my-2 overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200 text-sm" {...props}>
          {children}
        </table>
      </div>
    ),
    thead: ({ node, children, ...props }) => (
      <thead className="bg-gray-50" {...props}>{children}</thead>
    ),
    th: ({ node, children, ...props }) => (
      <th className="px-3 py-1.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider" {...props}>
        {children}
      </th>
    ),
    td: ({ node, children, ...props }) => (
      <td className="px-3 py-1.5 text-sm text-gray-700 border-t" {...props}>{children}</td>
    ),
    // Style paragraphs
    p: ({ node, children, ...props }) => {
      // Check if parent is a list item
      const isInListItem = node.parent?.type === 'listItem';
      return (
        <p className={`${isInListItem ? 'mb-0.5' : 'mb-1.5'} text-sm`} {...props}>
          {children}
        </p>
      );
    },
    // Custom text renderer to handle visualization mentions
    text: ({ node, children, ...props }) => {
      // Check if the text contains a mention
      const text = String(children);
      if (text.includes('@fig:') || text.includes('@signal:')) {
        return (
          <span 
            dangerouslySetInnerHTML={{ 
              __html: highlightMentions(text) 
            }} 
            {...props} 
          />
        );
      }
      return <span {...props}>{children}</span>;
    }
  };

  if (isTyping) {
    return (
      <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 px-4`}>
        <div className="flex items-center space-x-2 px-4 py-3 rounded-lg bg-gray-50 shadow-sm">
          <div className="animate-pulse flex space-x-1.5">
            <div className="h-2 w-2 bg-gray-400 rounded-full"></div>
            <div className="h-2 w-2 bg-gray-400 rounded-full animation-delay-200"></div>
            <div className="h-2 w-2 bg-gray-400 rounded-full animation-delay-400"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-2 px-3`}>
      <div 
        className={`max-w-[90%] break-words rounded-2xl shadow-sm text-left
          ${isUser 
            ? 'bg-primary-main text-black rounded-br-sm' 
            : 'bg-white text-gray-800 rounded-bl-sm border border-gray-100'
          } px-3 py-2`}
      >
        <div className={`text-sm whitespace-pre-wrap overflow-wrap-anywhere text-left
          ${isError ? 'text-red-500' : ''}`}
        >
          {isUser ? (
            // For user messages, just highlight mentions
            <div className="text-left" dangerouslySetInnerHTML={{ __html: highlightMentions(text) }} />
          ) : (
            // For AI messages, use markdown with mention highlighting
            <div className={`prose ${isUser ? 'prose-invert' : ''} max-w-none prose-sm 
              prose-headings:mt-1.5 prose-headings:mb-1 
              prose-p:mb-1.5 prose-p:
              prose-pre:my-1.5 prose-img:my-1.5 prose-hr:my-2 
              prose-ul:my-0.5 prose-ol:my-0.5 
              prose-li:my-0 prose-li:mb-0.5
              text-left`}
            >
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={components}
              >
                {text}
              </ReactMarkdown>
            </div>
          )}
        </div>
        <div className={`text-xs mt-1 flex items-center ${isUser ? 'text-white/70 justify-end' : 'text-gray-400'}`}>
          {timestamp ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
        </div>
      </div>
    </div>
  );
};

Message.propTypes = {
  text: PropTypes.string.isRequired,
  isUser: PropTypes.bool.isRequired,
  timestamp: PropTypes.string.isRequired,
  isError: PropTypes.bool,
  isTyping: PropTypes.bool
};

Message.defaultProps = {
  isError: false
};

export default Message; 