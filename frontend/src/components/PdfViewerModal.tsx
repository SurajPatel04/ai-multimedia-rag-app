import React from "react";
import { IconX } from "@tabler/icons-react";
import { Worker, Viewer } from "@react-pdf-viewer/core";
import { defaultLayoutPlugin } from "@react-pdf-viewer/default-layout";
import { searchPlugin } from "@react-pdf-viewer/search";
import mammoth from "mammoth";
import * as XLSX from "xlsx";
import "@react-pdf-viewer/core/lib/styles/index.css";
import "@react-pdf-viewer/default-layout/lib/styles/index.css";
import "@react-pdf-viewer/search/lib/styles/index.css";

interface PdfViewerModalProps {
  url: string;
  fileName?: string;
  initialPage?: number;
  searchQuery?: string;
  onClose: () => void;
}

const PdfViewerModalComponent: React.FC<PdfViewerModalProps> = ({ url, fileName, initialPage, searchQuery, onClose }) => {
  const [isLoaded, setIsLoaded] = React.useState(false);
  const [csvText, setCsvText] = React.useState<string | null>(null);
  const [wordHtml, setWordHtml] = React.useState<string | null>(null);
  const [excelHtml, setExcelHtml] = React.useState<string | null>(null);

  React.useEffect(() => {
    setIsLoaded(false);
    if (fileName && fileName.endsWith('.csv')) {
      fetch(url)
        .then(res => res.text())
        .then(text => {
          setCsvText(text);
          setIsLoaded(true);
        })
        .catch(err => {
          console.error("Failed to fetch CSV", err);
          setCsvText("Error loading CSV file.");
        });
    } else if (fileName && (fileName.endsWith('.docx') || fileName.endsWith('.doc'))) {
      fetch(url)
        .then(res => res.arrayBuffer())
        .then(buffer => mammoth.convertToHtml({ arrayBuffer: buffer }))
        .then(result => {
          setWordHtml(result.value);
          setIsLoaded(true);
        })
        .catch(err => {
          console.error("Failed to fetch Word document", err);
          setWordHtml("<p class='text-red-500'>Error loading Word file.</p>");
        });
    } else if (fileName && (fileName.endsWith('.xlsx') || fileName.endsWith('.xls'))) {
      fetch(url)
        .then(res => res.arrayBuffer())
        .then(buffer => {
          const workbook = XLSX.read(buffer, { type: 'array' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          const html = XLSX.utils.sheet_to_html(worksheet);
          setExcelHtml(html);
          setIsLoaded(true);
        })
        .catch(err => {
          console.error("Failed to fetch Excel document", err);
          setExcelHtml("<p class='text-red-500'>Error loading Excel file.</p>");
        });
    }
  }, [url, fileName]);

  const searchPluginInstance = searchPlugin();
  const defaultLayoutPluginInstance = defaultLayoutPlugin({
    sidebarTabs: () => [],
  });

  const { highlight, jumpToMatch, jumpToNextMatch } = searchPluginInstance;

  React.useEffect(() => {
    if (isLoaded && searchQuery) {
      // IMPORTANT: Do NOT strip punctuation. We are doing an exact string search!
      const words = searchQuery.trim().split(/\s+/).filter(Boolean);
        
      if (words.length > 0) {
        // Use first 8 words to find the starting location
        const shortQuery = words.slice(0, 8).join(' ');
        
        setTimeout(() => {
          const tryScroll = (query: string) => {
            return highlight(query).then(matches => {
              if (matches && matches.length > 0) {
                // Secretly scroll the viewer exactly to the first matched text
                if (jumpToMatch) {
                    jumpToMatch(0);
                } else {
                    jumpToNextMatch();
                }
                return true;
              }
              return false;
            }).catch(e => {
                console.error("PDF Search Highlight Error:", e);
                return false;
            });
          };

          tryScroll(shortQuery).then(success => {
             if (!success && words.length > 4) {
                 // Fallback to 4 words if the first 8 had a typo
                 tryScroll(words.slice(0, 4).join(' '));
             }
          });
        }, 400);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, searchQuery]);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 sm:p-4">
      <style>
        {`
          /* Hide the Open File (upload) icon from the toolbar */
          [aria-label="Open file"], 
          [aria-label="Open document"],
          button[title="Open file"] {
            display: none !important;
          }
          
          /* Make the highlights completely invisible so it only acts as an auto-scroller */
          .rpv-search__highlight {
            background-color: transparent !important;
            border: none !important;
          }
          .rpv-search__highlight--current {
            background-color: transparent !important;
            border: none !important;
          }
        `}
      </style>
      <div className="relative flex h-full w-full sm:h-[90vh] sm:w-[90vw] flex-col rounded-none sm:rounded-xl border-0 sm:border border-neutral-800 bg-neutral-900 shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between border-b border-neutral-800 px-4 py-3 shrink-0">
          <h3 className="text-sm font-semibold text-white line-clamp-1 pr-4">{fileName || "PDF Viewer"}</h3>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-800 hover:text-white transition-colors shrink-0 bg-neutral-800/50 sm:bg-transparent"
          >
            <IconX className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 overflow-hidden bg-white relative">
          {fileName && fileName.endsWith('.csv') ? (
            <div className="h-full w-full overflow-auto bg-neutral-950 p-6">
               <pre className="text-[13px] text-neutral-300 font-mono whitespace-pre-wrap leading-relaxed">
                  {csvText || "Loading CSV data..."}
               </pre>
            </div>
          ) : fileName && (fileName.endsWith('.docx') || fileName.endsWith('.doc')) ? (
            <div className="h-full w-full overflow-auto bg-white p-8 sm:p-12 text-black prose prose-sm sm:prose-base max-w-none">
                {wordHtml ? (
                    <div dangerouslySetInnerHTML={{ __html: wordHtml }} />
                ) : (
                    <div className="flex items-center justify-center h-full text-neutral-500 font-medium">Loading Word Document...</div>
                )}
            </div>
          ) : fileName && ['xlsx', 'xls'].includes(fileName.split('.').pop()?.toLowerCase() || '') ? (
            <div className="h-full w-full overflow-auto bg-white p-8 sm:p-12 text-black">
                <style>
                  {`
                    table { border-collapse: collapse; width: 100%; font-size: 14px; }
                    th, td { border: 1px solid #ccc; padding: 6px 12px; text-align: left; }
                    th { background-color: #f3f4f6; font-weight: bold; }
                    tr:nth-child(even) { background-color: #f9fafb; }
                  `}
                </style>
                {excelHtml ? (
                    <div dangerouslySetInnerHTML={{ __html: excelHtml }} />
                ) : (
                    <div className="flex items-center justify-center h-full text-neutral-500 font-medium">Loading Excel Document...</div>
                )}
            </div>
          ) : (
            <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
              <Viewer
                fileUrl={url}
                plugins={[defaultLayoutPluginInstance, searchPluginInstance]}
                theme="dark"
                initialPage={initialPage ? initialPage - 1 : 0}
                onDocumentLoad={() => setIsLoaded(true)}
              />
            </Worker>
          )}
        </div>
      </div>
    </div>
  );
};

export const PdfViewerModal = React.memo(PdfViewerModalComponent, (prevProps, nextProps) => {
  return prevProps.url === nextProps.url && prevProps.fileName === nextProps.fileName && prevProps.initialPage === nextProps.initialPage && prevProps.searchQuery === nextProps.searchQuery;
});
