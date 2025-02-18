document.addEventListener("DOMContentLoaded", () => {
  const categoriesContainer = document.getElementById("emoji-categories");
  const addCategoryForm = document.getElementById("add-category-form");

  // 获取中文-英文映射
  async function fetchEmotions() {
    try {
      const response = await fetch("/api/emotions");
      if (!response.ok) throw new Error("响应异常");
      return await response.json();
    } catch (error) {
      console.error("加载 emotions.json 失败", error);
      return {};
    }
  }

  // 获取所有表情包数据
  async function fetchEmojis() {
    try {
      const [emojiResponse, emotionMap] = await Promise.all([
        fetch("/api/emoji").then((res) => {
          if (!res.ok) throw new Error("获取表情包数据失败");
          return res.json();
        }),
        fetchEmotions(),
      ]);
      displayCategories(emojiResponse, emotionMap);
      updateSidebar(emojiResponse, emotionMap); // 更新侧边栏目录
    } catch (error) {
      console.error("加载表情包数据失败", error);
    }
  }

  // 反向查找中文名称
  function getChineseName(emotionMap, category) {
    for (const [chinese, english] of Object.entries(emotionMap)) {
      if (english === category) {
        return chinese;
      }
    }
    return category;
  }

  // 根据数据生成 DOM 节点，展示每个分类及其表情包，并添加上传块
  function displayCategories(data, emotionMap) {
    if (!categoriesContainer) return;
    categoriesContainer.innerHTML = "";

    for (const category in data) {
      // 创建分类容器，并添加 id 用于锚点跳转（注意 id 不要包含空格或特殊字符）
      const categoryDiv = document.createElement("div");
      categoryDiv.classList.add("category");
      categoryDiv.id = "category-" + category; // 使用英文名称

      // 分类标题：中文名（英文名）
      const categoryTitle = document.createElement("h3");
      const chineseName = getChineseName(emotionMap, category);
      categoryTitle.textContent = `${chineseName} (${category})`;

      // 创建标题容器用于标题和删除分类按钮
      const headerDiv = document.createElement("div");
      headerDiv.style.display = "flex";
      headerDiv.style.justifyContent = "space-between";
      headerDiv.style.alignItems = "center";
      headerDiv.appendChild(categoryTitle);

      // 删除分类按钮
      const deleteCategoryBtn = document.createElement("button");
      deleteCategoryBtn.classList.add("delete-category-btn");
      deleteCategoryBtn.textContent = "删除分类";
      deleteCategoryBtn.addEventListener("click", () =>
        deleteCategory(category)
      );
      headerDiv.appendChild(deleteCategoryBtn);

      categoryDiv.appendChild(headerDiv);

      // 创建表情列表容器
      const emojiListDiv = document.createElement("div");
      emojiListDiv.classList.add("emoji-list");

      // 遍历已有表情包
      data[category].forEach((emoji) => {
        const emojiItem = document.createElement("div");
        emojiItem.classList.add("emoji-item");

        // 使用懒加载的背景图片（设置 data-bg 属性用于懒加载）
        emojiItem.setAttribute("data-bg", `/memes/${category}/${emoji}`);

        // 删除按钮（右上角）
        const deleteBtn = document.createElement("button");
        deleteBtn.classList.add("delete-btn");
        deleteBtn.textContent = "×";
        deleteBtn.addEventListener("click", () => deleteEmoji(category, emoji));
        emojiItem.appendChild(deleteBtn);

        emojiListDiv.appendChild(emojiItem);
      });

      // 上传块：拖拽或点击上传新的表情包
      const uploadBlock = document.createElement("div");
      uploadBlock.classList.add("upload-emoji");
      uploadBlock.textContent = "拖拽或点击上传";

      // 隐藏的文件输入
      const fileInput = document.createElement("input");
      fileInput.type = "file";
      fileInput.accept = "image/*";
      fileInput.style.display = "none";
      uploadBlock.appendChild(fileInput);

      // 点击上传块打开文件选择对话框
      uploadBlock.addEventListener("click", () => {
        fileInput.click();
      });
      // 文件选择后上传
      fileInput.addEventListener("change", () => {
        if (fileInput.files && fileInput.files[0]) {
          uploadEmoji(category, fileInput.files[0]);
        }
      });
      // 拖拽事件
      uploadBlock.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadBlock.classList.add("dragover");
      });
      uploadBlock.addEventListener("dragleave", (e) => {
        e.preventDefault();
        uploadBlock.classList.remove("dragover");
      });
      uploadBlock.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadBlock.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
          uploadEmoji(category, e.dataTransfer.files[0]);
        }
      });

      emojiListDiv.appendChild(uploadBlock);
      categoryDiv.appendChild(emojiListDiv);
      categoriesContainer.appendChild(categoryDiv);
    }

    // 懒加载背景图片
    const lazyBackgrounds = document.querySelectorAll(".emoji-item");

    const observer = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const emojiItem = entry.target;
            const bgUrl = emojiItem.getAttribute("data-bg");
            emojiItem.style.backgroundImage = `url('${bgUrl}')`; // 加载背景图片
            emojiItem.removeAttribute("data-bg"); // 移除临时属性
            observer.unobserve(emojiItem); // 停止观察
          }
        });
      },
      { threshold: 0.1 }
    );

    lazyBackgrounds.forEach((item) => {
      observer.observe(item); // 观察每个表情包
    });
  }

  // 更新侧边栏目录，根据分类数据生成跳转链接
  function updateSidebar(data, emotionMap) {
    const sidebarList = document.getElementById("sidebar-list");
    if (!sidebarList) return;
    sidebarList.innerHTML = "";

    for (const category in data) {
      const li = document.createElement("li");
      const chineseName = getChineseName(emotionMap, category);
      const a = document.createElement("a");
      a.href = "#category-" + category; // 点击后跳转到对应 id 的分类
      a.textContent = chineseName;
      li.appendChild(a);
      sidebarList.appendChild(li);
    }
  }

  // 上传表情包
  async function uploadEmoji(category, file) {
    const formData = new FormData();
    formData.append("category", category);
    formData.append("image_file", file);

    try {
      const response = await fetch("/api/emoji/add", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        console.error("添加表情包失败，响应异常");
      }
      fetchEmojis();
    } catch (error) {
      console.error("添加表情包失败", error);
    }
  }

  // 删除表情包
  async function deleteEmoji(category, emoji) {
    if (!confirm("是否删除该表情包？")) return;
    if (!confirm("请再次确认删除该表情包，此操作不可恢复！")) return;
    try {
      const response = await fetch("/api/emoji/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category, image_file: emoji }),
      });
      if (!response.ok) {
        console.error("删除表情包失败，响应异常");
      }
      fetchEmojis();
    } catch (error) {
      console.error("删除表情包失败", error);
    }
  }

  // 删除表情包类别
  async function deleteCategory(category) {
    if (!confirm("是否删除该分类及其所有表情包？")) return;
    if (!confirm("请再次确认删除该分类，此操作不可恢复！")) return;
    try {
      const response = await fetch("/api/category/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category }),
      });
      if (!response.ok) {
        console.error("删除分类失败，响应异常");
      }
      fetchEmojis();
    } catch (error) {
      console.error("删除分类失败", error);
    }
  }

  // 添加分类：通过新表单输入中文名称和英文名称
  const addCategoryBtn = document.getElementById("add-category-btn");
  if (addCategoryBtn && addCategoryForm) {
    addCategoryBtn.addEventListener("click", () => {
      addCategoryForm.style.display = "block";
    });
  }
  const saveCategoryBtn = document.getElementById("save-category-btn");
  if (saveCategoryBtn) {
    saveCategoryBtn.addEventListener("click", async () => {
      const chineseInput = document.getElementById("new-category-chinese");
      const englishInput = document.getElementById("new-category-english");
      const chineseName = chineseInput?.value.trim();
      const englishName = englishInput?.value.trim();
      if (chineseName && englishName) {
        try {
          const response = await fetch("/api/category/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              chinese: chineseName,
              english: englishName,
            }),
          });
          if (!response.ok) {
            console.error("添加分类失败，响应异常");
          }
          addCategoryForm.style.display = "none";
          // 清空输入框
          chineseInput.value = "";
          englishInput.value = "";
          fetchEmojis();
        } catch (error) {
          console.error("添加分类失败", error);
        }
      }
    });
  }

  // 初始化加载数据
  fetchEmojis();
});
