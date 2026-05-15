import api from "./api";

export interface UploadedFileInfo {
  original_name: string;
  saved_name: string;
  content_type: string;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  temp_id: string;
  data: UploadedFileInfo[];
}

export const uploadFiles = async (
  files: File[],
  tempId?: string | null,
  signal?: AbortSignal
): Promise<UploadResponse> => {
  const formData = new FormData();

  files.forEach((file) => {
    formData.append("files", file);
  });

  if (tempId) {
    formData.append("temp_id", tempId);
  }

  const res = await api.post<UploadResponse>("/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    signal,
  });

  return res.data;
};
