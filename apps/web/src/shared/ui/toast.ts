import { Toast } from '@base-ui/react/toast';

const toastManager = Toast.createToastManager();

const toast = {
  success(title: string, description?: string) {
    return toastManager.add({ title, type: 'success', ...(description ? { description } : {}) });
  },
  info(title: string, description?: string) {
    return toastManager.add({ title, type: 'info', ...(description ? { description } : {}) });
  },
  error(title: string, description?: string) {
    return toastManager.add({
      title,
      type: 'error',
      priority: 'high',
      ...(description ? { description } : {}),
    });
  },
};

export { toast, toastManager };
