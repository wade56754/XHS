import { createStorage, StorageEnum } from '../base/index.js';
import type { XhsAuthorDataType, XhsAuthorStorageType } from '../base/index.js';

const storage = createStorage<XhsAuthorDataType[]>(
  'xhs-author-storage-key',
  [],
  {
    storageEnum: StorageEnum.Local,
    liveUpdate: true,
    serialization: {
      serialize: (value: XhsAuthorDataType[]) => JSON.stringify(value),
      deserialize: (text: string) => {
        try {
          return JSON.parse(text) as XhsAuthorDataType[];
        } catch {
          return [];
        }
      },
    },
  },
);

export const xhsAuthorStorage: XhsAuthorStorageType = {
  ...storage,
  addAuthor: async (authorData) => {
    const id = Date.now().toString() + Math.random().toString(36).substr(2, 9);
    const createdAt = new Date().toISOString();
    
    await storage.set(currentAuthors => [
      ...currentAuthors,
      {
        ...authorData,
        id,
        createdAt,
      },
    ]);
  },
  removeAuthor: async (id) => {
    await storage.set(currentAuthors => 
      currentAuthors.filter(author => author.id !== id)
    );
  },
  clearAll: async () => {
    await storage.set([]);
  },
};