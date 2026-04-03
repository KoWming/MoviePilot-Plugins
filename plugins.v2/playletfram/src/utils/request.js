// API 请求封装工具
// 用于开发模式下模拟 MoviePilot 主应用的 API 调用

/**
 * 创建请求实例
 * @param {string} baseURL - 基础 URL
 * @returns {Object} 请求对象
 */
export function createRequest(baseURL = '') {
    const request = async (url, options = {}) => {
        const fullUrl = baseURL ? `${baseURL}${url}` : url;

        try {
            const response = await fetch(fullUrl, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers,
                },
                ...options,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Request failed:', error);
            throw error;
        }
    };

    return {
        get: (url, config = {}) => request(url, { method: 'GET', ...config }),
        post: (url, data, config = {}) => request(url, {
            method: 'POST',
            body: JSON.stringify(data),
            ...config,
        }),
        put: (url, data, config = {}) => request(url, {
            method: 'PUT',
            body: JSON.stringify(data),
            ...config,
        }),
        delete: (url, config = {}) => request(url, { method: 'DELETE', ...config }),
    };
}

export default createRequest;
