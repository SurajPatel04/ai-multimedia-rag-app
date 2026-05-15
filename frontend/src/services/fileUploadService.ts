import api from "./api";

export interface UploadedFileInfo {
  original_name: string;
  saved_name: string;
  content_type: string;
  file_id: string;
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

export const cancelFile = async (tempId: string, fileId: string) => {
  const res = await api.delete(`/upload/cancel/${tempId}/${fileId}`);
  return res.data;
};
