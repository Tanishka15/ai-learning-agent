document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatArea = document.getElementById('chat-area');
    const classroomCoursesDiv = document.getElementById('classroom-courses');
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Initialize classroom agent when page loads
    initializeClassroomAgent();
    
    // Auto-resize the textarea as user types
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        const newHeight = Math.min(this.scrollHeight, 150);
        this.style.height = newHeight + 'px';
    });

    // Handle form submission
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const userMsg = chatInput.value.trim();
        if (!userMsg) return;
        
        // Check if reasoning chain toggle is enabled
        const showReasoning = document.getElementById('show-reasoning-toggle')?.checked || false;
        
        // Display user message
        appendMessage(userMsg, 'user');
        
        // Clear input and reset height
        chatInput.value = '';
        chatInput.style.height = 'auto';
        chatInput.focus();
        
        // Show typing indicator
        showTypingIndicator();
        
        try {
            // Send to backend with reasoning chain toggle state
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    message: userMsg,
                    show_reasoning: showReasoning
                })
            });
            
            // Remove typing indicator
            hideTypingIndicator();
            
            if (response.ok) {
                const data = await response.json();
                
                // Add a brief delay for better UX
                setTimeout(() => {
                    // Display agent response with typing effect
                    typeMessage(data.reply);
                }, 300);
                
                // Check if we have a reasoning chain to display
                if (data.has_reasoning && data.reasoning) {
                    // Add a small delay to allow the main answer to finish typing
                    setTimeout(() => {
                        // Add a reasoning chain toggle button
                        const reasoningToggle = document.createElement('div');
                        reasoningToggle.className = 'reasoning-toggle';
                        reasoningToggle.innerHTML = `
                            <button class="btn btn-sm btn-outline-light mt-2" id="toggle-reasoning-btn">
                                <i class="bi bi-lightbulb me-1"></i> Show Reasoning Process
                            </button>
                        `;
                        chatArea.appendChild(reasoningToggle);
                        
                        // Create a hidden reasoning section
                        const reasoningSection = document.createElement('div');
                        reasoningSection.className = 'reasoning-section d-none';
                        reasoningSection.id = `reasoning-${Date.now()}`;
                        
                        // Format the reasoning chain for regular chat
                        let formattedReasoning = data.reasoning
                            .replace(/\n/g, '<br>')
                            .replace(/STEP (\d+): ([A-Z_]+)/g, '<div class="reasoning-step-title"><i class="bi bi-gear me-2"></i>Step $1: $2</div>')
                            .replace(/🔎/g, '<i class="bi bi-search text-primary"></i>')
                            .replace(/⮕/g, '<i class="bi bi-arrow-right text-success"></i>')
                            .replace(/⏱️/g, '<i class="bi bi-clock text-info"></i>')
                            .replace(/📊/g, '<i class="bi bi-graph-up text-warning"></i>')
                            .replace(/🧠 REASONING PROCESS/g, '<div class="reasoning-header"><i class="bi bi-cpu me-2"></i>AI Reasoning Process</div>')
                            .replace(/🧠 REASONING CHAIN/g, '<div class="reasoning-header"><i class="bi bi-cpu me-2"></i>AI Reasoning Process</div>')
                            // Add spacing after each step
                            .replace(/(<\/div>)(<br>⮕)/g, '$1<br>$2')
                            // Make duration info smaller and styled
                            .replace(/Duration: ([0-9.]+s)/g, '<small class="text-muted"><i class="bi bi-stopwatch me-1"></i>$1</small>');
                        
                        reasoningSection.innerHTML = `
                            <div class="reasoning-container mt-3 p-3 border rounded">
                                ${formattedReasoning}
                            </div>
                        `;
                        
                        chatArea.appendChild(reasoningSection);
                        
                        // Add event listener to the toggle button
                        document.getElementById('toggle-reasoning-btn').addEventListener('click', function() {
                            const reasoningDiv = document.getElementById(`reasoning-${Date.now()}`);
                            if (reasoningDiv.classList.contains('d-none')) {
                                // Show reasoning
                                reasoningDiv.classList.remove('d-none');
                                this.innerHTML = '<i class="bi bi-lightbulb-off me-1"></i> Hide Reasoning Process';
                            } else {
                                // Hide reasoning
                                reasoningDiv.classList.add('d-none');
                                this.innerHTML = '<i class="bi bi-lightbulb me-1"></i> Show Reasoning Process';
                            }
                            scrollToBottom();
                        });
                        
                        scrollToBottom();
                    }, 1000); // Wait 1 second after main answer finishes typing
                }
                
                // Save to chat history (just the answer portion, not the reasoning)
                saveChatHistory(userMsg, data.reply);
            } else {
                const errorMsg = 'Sorry, I encountered an error processing your request.';
                appendMessage(errorMsg, 'agent');
                saveChatHistory(userMsg, errorMsg);
            }
        } catch (error) {
            hideTypingIndicator();
            const errorMsg = 'Network error. Please check your connection and try again.';
            appendMessage(errorMsg, 'agent');
            saveChatHistory(userMsg, errorMsg);
            console.error('Error:', error);
        }
    });

    // Load Google Classroom courses if user is logged in
    if (classroomCoursesDiv) {
        loadClassroomCourses();
    }
    
    // Add event listener for study plan button
    document.getElementById('study-plan-btn')?.addEventListener('click', showStudyPlanDialog);

    // Sidebar button handlers
    document.getElementById('courses-btn')?.addEventListener('click', function() {
        appendMessage('Show me my courses', 'user');
        showTypingIndicator();
        
        // Fetch actual classroom courses instead of predefined topics
        fetch('/api/courses')
            .then(response => response.json())
            .then(data => {
                hideTypingIndicator();
                typeMessage('Here are your Google Classroom courses:');
                
                setTimeout(() => {
                    const coursesList = document.createElement('div');
                    coursesList.className = 'message agent-message';
                    
                    if (!data.courses || data.courses.length === 0) {
                        coursesList.innerHTML = `<div class="p-3">No courses found in your Google Classroom.</div>`;
                    } else {
                        const coursesHtml = data.courses.map(course => 
                            `<div class="topic-item mb-2">
                                <button class="btn btn-sm btn-outline-light topic-btn" data-course-id="${course.id}" data-course-name="${course.name}">
                                    ${course.name}
                                </button>
                            </div>`
                        ).join('');
                        
                        coursesList.innerHTML = `<div class="topics-list">${coursesHtml}</div>`;
                    }
                    
                    chatArea.appendChild(coursesList);
                    
                    // Add event listeners to course buttons
                    document.querySelectorAll('.topic-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            const courseName = this.getAttribute('data-course-name');
                            appendMessage(`Tell me about my ${courseName} course`, 'user');
                            
                            showTypingIndicator();
                            setTimeout(() => {
                                hideTypingIndicator();
                                typeMessage(`I'll help you with your ${courseName} course. What would you like to know about it?`);
                            }, 1000);
                        });
                    });
                    
                    scrollToBottom();
                }, 500);
            })
            .catch(error => {
                hideTypingIndicator();
                appendMessage("I couldn't retrieve your courses at this time. Please try again later.", 'agent');
                console.error('Error fetching courses:', error);
            });
    });

    document.getElementById('stats-btn')?.addEventListener('click', function() {
        appendMessage('Show my learning statistics', 'user');
        showTypingIndicator();
        
        // Get chat history to calculate real statistics
        const chatHistory = getChatHistory();
        const questionCount = chatHistory.length;
        
        // Calculate other stats based on actual usage
        const uniqueTopics = new Set();
        let totalTextLength = 0;
        
        chatHistory.forEach(item => {
            // Extract potential topics from questions (simple word extraction)
            const words = item.question.toLowerCase().match(/\b\w{4,}\b/g) || [];
            words.forEach(word => {
                if (!['what', 'where', 'when', 'which', 'about', 'explain', 'tell', 'show'].includes(word)) {
                    uniqueTopics.add(word);
                }
            });
            
            // Add up response lengths to estimate time spent
            totalTextLength += item.answer.length;
        });
        
        // Convert text length to approximate time spent (rough estimate)
        const timeSpent = Math.max(0.5, (totalTextLength / 2000).toFixed(1));
        
        // Calculate knowledge score based on activity (more conversations = higher score)
        const knowledgeScore = Math.min(95, Math.round(50 + (questionCount * 2)));
        
        setTimeout(() => {
            hideTypingIndicator();
            typeMessage('Here\'s a summary of your learning progress based on your activity:');
            
            // Dynamic statistics UI
            const statsDiv = document.createElement('div');
            statsDiv.className = 'message agent-message';
            statsDiv.innerHTML = `
                <div class="stats-container p-2">
                    <div class="row g-2">
                        <div class="col-6">
                            <div class="p-3 border rounded bg-dark">
                                <h6 class="text-light">Topics Explored</h6>
                                <h3 class="text-light">${Math.min(uniqueTopics.size, 30)}</h3>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="p-3 border rounded bg-dark">
                                <h6 class="text-light">Questions Asked</h6>
                                <h3 class="text-light">${questionCount}</h3>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="p-3 border rounded bg-dark">
                                <h6 class="text-light">Time Spent</h6>
                                <h3 class="text-light">${timeSpent} hrs</h3>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="p-3 border rounded bg-dark">
                                <h6 class="text-light">Knowledge Score</h6>
                                <h3 class="text-light">${knowledgeScore}%</h3>
                            </div>
                        </div>
                    </div>
                    <p class="text-light small mt-2">
                        <em>Statistics are based on your conversation history and activity with the learning assistant.</em>
                    </p>
                </div>
            `;
            chatArea.appendChild(statsDiv);
            scrollToBottom();
        }, 1000);
    });

    document.getElementById('help-btn')?.addEventListener('click', function() {
        appendMessage('I need help using this system', 'user');
        showTypingIndicator();
        setTimeout(() => {
            hideTypingIndicator();
            typeMessage(`
                Here's how you can use this AI Learning Assistant:
                
                1. Ask any question on a topic you're interested in learning about.
                2. Request "teach me about [topic]" for an interactive learning session.
                3. Ask "what topics can you teach?" to see available subjects.
                4. Use the sidebar to navigate between different features.
                5. Connect your Google Classroom account to integrate with your classes.
                
                Is there something specific you'd like to learn about?
            `);
        }, 1000);
    });
    
    // Add event listener for history button
    document.getElementById('history-btn')?.addEventListener('click', function() {
        appendMessage('Show my chat history', 'user');
        showTypingIndicator();
        
        // Get chat history from local storage
        const chatHistory = getChatHistory();
        
        setTimeout(() => {
            hideTypingIndicator();
            
            if (chatHistory.length === 0) {
                typeMessage("You don't have any previous chat history yet.");
            } else {
                typeMessage("Here's a summary of your recent conversations:");
                
                setTimeout(() => {
                    const historyDiv = document.createElement('div');
                    historyDiv.className = 'message agent-message';
                    
                    let historyHtml = '<div class="chat-history p-3 border rounded text-light">';
                    historyHtml += '<h5 class="text-light mb-3">Recent Conversations</h5>';
                    
                    // Show last 5 conversations or all if less than 5
                    const recentHistory = chatHistory.slice(-5).reverse();
                    
                    recentHistory.forEach((item, index) => {
                        historyHtml += `
                            <div class="history-item mb-3 pb-2 border-bottom border-secondary">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <strong class="text-light">${new Date(item.timestamp).toLocaleString()}</strong>
                                </div>
                                <div class="user-question mb-1 text-light"><strong>You:</strong> ${item.question}</div>
                                <div class="agent-answer text-light"><strong>Agent:</strong> ${item.answer.substring(0, 100)}${item.answer.length > 100 ? '...' : ''}</div>
                            </div>
                        `;
                    });
                    
                    historyHtml += '</div>';
                    historyDiv.innerHTML = historyHtml;
                    
                    chatArea.appendChild(historyDiv);
                    scrollToBottom();
                }, 500);
            }
        }, 1000);
    });

    // Helper function to load Google Classroom courses
    async function loadClassroomCourses() {
        try {
            const response = await fetch('/api/courses');
            if (!response.ok) {
                throw new Error('Failed to fetch courses');
            }
            
            const data = await response.json();
            
            if (!data.courses || data.courses.length === 0) {
                classroomCoursesDiv.innerHTML = '<p class="text-muted small px-3">No courses found</p>';
                return;
            }
            
            const coursesHtml = data.courses.map(course => `
                <a href="#" class="course-item d-flex align-items-center text-decoration-none px-3 py-2" data-course-id="${course.id}">
                    <i class="bi bi-journal-text me-2 text-light"></i>
                    <div class="small text-truncate text-light">${course.name}</div>
                </a>
            `).join('');
            
            classroomCoursesDiv.innerHTML = coursesHtml;
            
            // Add event listeners to course items
            document.querySelectorAll('.course-item').forEach(item => {
                item.addEventListener('click', function(e) {
                    e.preventDefault();
                    const courseId = this.getAttribute('data-course-id');
                    const courseName = this.querySelector('div').textContent;
                    
                    appendMessage(`Tell me about my ${courseName} class`, 'user');
                    showTypingIndicator();
                    
                    // No need to fetch students, just show course info directly
                    setTimeout(() => {
                        hideTypingIndicator();
                        typeMessage(`Here's information about your ${courseName} class:`);
                        
                        setTimeout(() => {
                            const courseInfoDiv = document.createElement('div');
                            courseInfoDiv.className = 'message agent-message';
                            
                            courseInfoDiv.innerHTML = `
                                <div class="course-info p-3 border rounded">
                                    <h5>${courseName}</h5>
                                    <p>What would you like to know about this course?</p>
                                </div>
                            `;
                            chatArea.appendChild(courseInfoDiv);
                            scrollToBottom();
                        }, 500);
                    }, 1000);
                });
            });
        } catch (error) {
            classroomCoursesDiv.innerHTML = '<p class="text-danger small px-3">Error loading courses</p>';
            console.error('Error loading classroom courses:', error);
        }
    }

    function appendMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message${sender === 'agent' ? ' enhanced' : ''}`;
        
        if (sender === 'agent') {
            // Apply enhanced formatting for agent messages
            const formattedContent = formatGeneralResponse(text);
            messageDiv.innerHTML = formattedContent;
        } else {
            // Simple text for user messages
            const paragraph = document.createElement('p');
            paragraph.textContent = text;
            messageDiv.appendChild(paragraph);
        }
        
        chatArea.appendChild(messageDiv);
        scrollToBottom();
    }
    
    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'message agent-message typing-indicator';
        indicator.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
        indicator.id = 'typing-indicator';
        chatArea.appendChild(indicator);
        scrollToBottom();
    }
    
    function hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    function typeMessage(text, index = 0) {
        if (index === 0) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message agent-message enhanced';
            messageDiv.id = 'current-typing';
            
            const paragraph = document.createElement('p');
            messageDiv.appendChild(paragraph);
            
            chatArea.appendChild(messageDiv);
        }
        
        const currentMessage = document.getElementById('current-typing');
        const paragraph = currentMessage.querySelector('p');
        
        if (index < text.length) {
            paragraph.textContent = text.substring(0, index + 1);
            scrollToBottom();
            setTimeout(() => typeMessage(text, index + 1), 15);
        } else {
            // Apply enhanced formatting after typing is complete
            const formattedContent = formatGeneralResponse(text);
            currentMessage.innerHTML = formattedContent;
            currentMessage.removeAttribute('id');
        }
    }
    
    // Function to format general responses with markdown-like support
    function formatGeneralResponse(text) {
        let formatted = text
            // Convert headers
            .replace(/^### (.*$)/gm, '<h3>$1</h3>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^# (.*$)/gm, '<h1>$1</h1>')
            
            // Convert bold and italic
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            
            // Convert code blocks
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            
            // Convert blockquotes
            .replace(/^> (.*$)/gm, '<blockquote>$1</blockquote>')
            
            // Convert bullet points
            .replace(/^[\s]*[-*+]\s+(.*$)/gm, '<li>$1</li>')
            
            // Convert numbered lists
            .replace(/^[\s]*\d+\.\s+(.*$)/gm, '<li>$1</li>')
            
            // Wrap consecutive list items in ul tags
            .replace(/(<li>.*<\/li>\s*)+/gs, function(match) {
                return '<ul>' + match + '</ul>';
            })
            
            // Clean up multiple line breaks and wrap paragraphs
            .replace(/\n\n+/g, '</p><p>')
            .replace(/\n/g, '<br>')
            
            // Highlight course mentions (pattern: letters followed by numbers)
            .replace(/\b([A-Z]{2,4}[\s-]?\d{2,4}[A-Za-z]*)\b/g, '<span class="course-mention">$1</span>')
            
            // Highlight dates (various formats)
            .replace(/\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b/g, '<span class="date-mention">$1</span>')
            .replace(/\b(\d{1,2}\/\d{1,2}\/\d{2,4})\b/g, '<span class="date-mention">$1</span>')
            .replace(/\b(\d{1,2}-\d{1,2}-\d{2,4})\b/g, '<span class="date-mention">$1</span>')
            .replace(/\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(st|nd|rd|th)?\b/g, '<span class="date-mention">$1</span>')
            
            // Highlight time
            .replace(/\b(\d{1,2}:\d{2}\s*[APap][Mm])\b/g, '<span class="date-mention">$1</span>')
            
            // Highlight priority indicators
            .replace(/\b(HIGH PRIORITY|URGENT|CRITICAL)\b/gi, '<span class="priority-high">$1</span>')
            .replace(/\b(MEDIUM PRIORITY|IMPORTANT)\b/gi, '<span class="priority-medium">$1</span>')
            .replace(/\b(LOW PRIORITY|OPTIONAL)\b/gi, '<span class="priority-low">$1</span>')
            
            // Create info boxes for special content
            .replace(/^(ℹ️|INFO|NOTE):\s*(.*$)/gm, '<div class="info-box">$2</div>')
            .replace(/^(⚠️|WARNING|ATTENTION):\s*(.*$)/gm, '<div class="warning-box">$2</div>')
            .replace(/^(✅|SUCCESS|COMPLETED):\s*(.*$)/gm, '<div class="success-box">$2</div>')
            
            // Wrap remaining text in paragraphs
            .replace(/^(?!<[hul]|<div|<blockquote)/gm, '<p>')
            .replace(/(?<!>)$/gm, '</p>')
            
            // Clean up empty paragraphs and fix spacing
            .replace(/<p><\/p>/g, '')
            .replace(/<p><br><\/p>/g, '')
            .replace(/<\/ul>\s*<ul>/g, '')
            .replace(/<\/blockquote>\s*<blockquote>/g, '<br>');
            
        return formatted;
    }
    
    function scrollToBottom() {
        chatArea.scrollTop = chatArea.scrollHeight;
    }
    
    // Chat history functions
    function saveChatHistory(question, answer) {
        // Get existing history or initialize empty array
        const existingHistory = getChatHistory();
        
        // Add new item
        existingHistory.push({
            question: question,
            answer: answer,
            timestamp: new Date().toISOString()
        });
        
        // Keep only the last 20 conversations
        const limitedHistory = existingHistory.slice(-20);
        
        // Save to local storage
        localStorage.setItem('chatHistory', JSON.stringify(limitedHistory));
    }
    
    function getChatHistory() {
        const history = localStorage.getItem('chatHistory');
        return history ? JSON.parse(history) : [];
    }
    
    // Function to initialize the classroom agent
    async function initializeClassroomAgent() {
        try {
            const response = await fetch('/api/classroom/initialize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            if (!result.success) {
                console.warn("Classroom agent initialization warning:", result.message);
            }
        } catch (error) {
            console.error("Failed to initialize classroom agent:", error);
        }
    }
    
    // Function to show study plan dialog
    function showStudyPlanDialog() {
        // First remove any existing study plan dialog to prevent duplicates
        const existingDialog = document.getElementById('study-plan-dialog');
        if (existingDialog) {
            existingDialog.remove();
        }
        
        appendMessage('Create a study plan', 'user');
        showTypingIndicator();
        
        // Make sure classroom agent is initialized first
        fetch('/api/classroom/initialize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(() => {
            // Now fetch courses for the dropdown
            return fetch('/api/courses');
        })
        .then(response => response.json())
        .then(data => {
            hideTypingIndicator();
            
            const studyPlanDialog = document.createElement('div');
            studyPlanDialog.className = 'message agent-message';
            studyPlanDialog.id = 'study-plan-dialog';
                
                // Create course options
                let courseOptions = '<option value="">All Courses</option>';
                if (data.courses && data.courses.length > 0) {
                    data.courses.forEach(course => {
                        courseOptions += `<option value="${course.name}">${course.name}</option>`;
                    });
                }
                
                studyPlanDialog.innerHTML = `
                    <div class="study-plan-form p-3 border rounded">
                        <h5>Create Study Plan</h5>
                        <div class="mb-3">
                            <label class="form-label text-light">Course</label>
                            <select class="form-select form-select-sm bg-dark text-light" id="study-plan-course">
                                ${courseOptions}
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label text-light">Time Period</label>
                            <select class="form-select form-select-sm bg-dark text-light" id="study-plan-timeframe">
                                <option value="week">Weekly (Next 7 days)</option>
                                <option value="month">Monthly (Next 30 days)</option>
                                <option value="all">Complete (All upcoming)</option>
                            </select>
                        </div>
                        <button class="btn btn-primary btn-sm" id="generate-study-plan-btn">Generate Plan</button>
                    </div>
                `;
                
                chatArea.appendChild(studyPlanDialog);
                scrollToBottom();
                
                // Add event listener for generate button with one-time execution
                const generateButton = document.getElementById('generate-study-plan-btn');
                if (generateButton) {
                    // Use once: true to ensure the event only fires once
                    generateButton.addEventListener('click', function handleGenerate() {
                        // Disable the button immediately to prevent multiple clicks
                        generateButton.disabled = true;
                        generateButton.textContent = 'Generating...';
                        
                        // Call the generate function
                        generateStudyPlan();
                        
                        // Remove the event listener after it's been used
                        generateButton.removeEventListener('click', handleGenerate);
                    });
                }
            })
            .catch(error => {
                hideTypingIndicator();
                appendMessage("I couldn't create a study plan at this time. Please try again later.", 'agent');
                console.error('Error fetching courses for study plan:', error);
            });
    }
    
    // Function to generate the study plan
    async function generateStudyPlan() {
        const course = document.getElementById('study-plan-course').value;
        const timeframe = document.getElementById('study-plan-timeframe').value;
        
        // Check if reasoning chain toggle is enabled
        const showReasoning = document.getElementById('show-reasoning-toggle')?.checked || false;
        
        // Show user's request
        const requestMessage = `Generate a ${timeframe}ly study plan${course ? ' for ' + course : ''}`;
        appendMessage(requestMessage, 'user');
        
        showTypingIndicator();
        
        try {
            // Ensure classroom agent is initialized again before generating the plan
            await fetch('/api/classroom/initialize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const response = await fetch('/api/study-plan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    course: course || null,
                    timeframe: timeframe,
                    show_reasoning: showReasoning
                })
            });
            
            hideTypingIndicator();
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server error: ${response.status}. ${errorText}`);
            }
            
            const data = await response.json();
            if (data.error) {
                appendMessage(`Error creating study plan: ${data.error}`, 'agent');
            } else if (data.study_plan) {
                // Format the study plan nicely
                const formattedPlan = document.createElement('div');
                formattedPlan.className = 'message agent-message';
                
                // Convert markdown-like sections to HTML with better formatting
                let planHtml = data.study_plan
                    // Convert headers
                    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
                    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
                    .replace(/^#### (.*$)/gm, '<h4>$1</h4>')
                    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
                    // Convert bold and italic
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    // Convert bullet points
                    .replace(/^[\s]*[-*+]\s+(.*$)/gm, '<li>$1</li>')
                    .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
                    // Convert numbered lists
                    .replace(/^[\s]*\d+\.\s+(.*$)/gm, '<li>$1</li>')
                    // Clean up multiple line breaks
                    .replace(/\n\n+/g, '</p><p>')
                    .replace(/\n/g, '<br>')
                    // Wrap in paragraphs
                    .replace(/^(?!<[hul])/gm, '<p>')
                    .replace(/(?<!>)$/gm, '</p>')
                    // Clean up empty paragraphs
                    .replace(/<p><\/p>/g, '')
                    .replace(/<p><br><\/p>/g, '')
                    // Fix nested lists
                    .replace(/<\/ul>\s*<ul>/g, '')
                    .replace(/<\/ol>\s*<ol>/g, '');
                
                formattedPlan.innerHTML = `<div class="study-plan">${planHtml}</div>`;
                chatArea.appendChild(formattedPlan);
                
                // Check if we have a reasoning chain to display
                if (data.has_reasoning && data.reasoning) {
                    // Add a small delay to allow the main answer to finish rendering
                    setTimeout(() => {
                        // Add a reasoning chain toggle button
                        const reasoningToggle = document.createElement('div');
                        reasoningToggle.className = 'reasoning-toggle';
                        reasoningToggle.innerHTML = `
                            <button class="btn btn-sm btn-outline-light mt-2" id="toggle-study-plan-reasoning-btn">
                                <i class="bi bi-lightbulb me-1"></i> Show Reasoning Process
                            </button>
                        `;
                        chatArea.appendChild(reasoningToggle);
                        
                        // Create a hidden reasoning section
                        const reasoningId = `study-plan-reasoning-${Date.now()}`;
                        const reasoningSection = document.createElement('div');
                        reasoningSection.className = 'reasoning-section d-none';
                        reasoningSection.id = reasoningId;
                        
                        // Format the reasoning chain for study plans
                        let formattedReasoning = data.reasoning
                            .replace(/\n/g, '<br>')
                            .replace(/STEP (\d+): ([A-Z_]+)/g, '<div class="reasoning-step-title"><i class="bi bi-gear me-2"></i>Step $1: $2</div>')
                            .replace(/🔎/g, '<i class="bi bi-search text-primary"></i>')
                            .replace(/⮕/g, '<i class="bi bi-arrow-right text-success"></i>')
                            .replace(/⏱️/g, '<i class="bi bi-clock text-info"></i>')
                            .replace(/📊/g, '<i class="bi bi-graph-up text-warning"></i>')
                            .replace(/🧠 REASONING PROCESS/g, '<div class="reasoning-header"><i class="bi bi-cpu me-2"></i>AI Reasoning Process</div>')
                            .replace(/🧠 REASONING CHAIN/g, '<div class="reasoning-header"><i class="bi bi-cpu me-2"></i>AI Reasoning Process</div>')
                            // Add spacing after each step
                            .replace(/(<\/div>)(<br>⮕)/g, '$1<br>$2')
                            // Make duration info smaller and styled
                            .replace(/Duration: ([0-9.]+s)/g, '<small class="text-muted"><i class="bi bi-stopwatch me-1"></i>$1</small>');
                        
                        reasoningSection.innerHTML = `
                            <div class="reasoning-container mt-3 p-3 border rounded">
                                ${formattedReasoning}
                            </div>
                        `;
                        
                        chatArea.appendChild(reasoningSection);
                        
                        // Add event listener to the toggle button
                        document.getElementById('toggle-study-plan-reasoning-btn').addEventListener('click', function() {
                            const reasoningDiv = document.getElementById(reasoningId);
                            if (reasoningDiv.classList.contains('d-none')) {
                                // Show reasoning
                                reasoningDiv.classList.remove('d-none');
                                this.innerHTML = '<i class="bi bi-lightbulb-off me-1"></i> Hide Reasoning Process';
                            } else {
                                // Hide reasoning
                                reasoningDiv.classList.add('d-none');
                                this.innerHTML = '<i class="bi bi-lightbulb me-1"></i> Show Reasoning Process';
                            }
                            scrollToBottom();
                        });
                        
                        scrollToBottom();
                    }, 500); // Wait 0.5 seconds after main answer finishes rendering
                }
                
                // Remove the study plan dialog to prevent duplicates
                const studyPlanDialog = document.getElementById('study-plan-dialog');
                if (studyPlanDialog) {
                    studyPlanDialog.remove();
                }
            } else {
                appendMessage('I could not generate a study plan with the available information.', 'agent');
            }
        } catch (error) {
            hideTypingIndicator();
            appendMessage('An error occurred while generating the study plan.', 'agent');
            console.error('Error generating study plan:', error);
        }
        
        scrollToBottom();
    }
    
    // Bulletin Board functionality
    async function loadBulletinBoard() {
        try {
            const response = await fetch('/api/bulletin-board');
            if (!response.ok) {
                throw new Error('Failed to fetch bulletin board data');
            }
            
            const data = await response.json();
            displayBulletinBoard(data.items || []);
            
        } catch (error) {
            console.error('Error loading bulletin board:', error);
            // Display error message in bulletin board
            const bulletinBoard = document.querySelector('.bulletin-board');
            if (bulletinBoard) {
                bulletinBoard.innerHTML = `
                    <div class="text-center text-muted py-3">
                        <i class="bi bi-exclamation-triangle"></i>
                        <div>Unable to load bulletin board</div>
                    </div>
                `;
            }
        }
    }
    
    function displayBulletinBoard(items) {
        const bulletinBoard = document.querySelector('.bulletin-board');
        if (!bulletinBoard) return;
        
        if (!items || items.length === 0) {
            bulletinBoard.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="bi bi-check-circle"></i>
                    <div>No urgent items</div>
                    <small>All caught up!</small>
                </div>
            `;
            return;
        }
        
        const itemsHTML = items.map(item => {
            const priorityClass = getPriorityClass(item.priority);
            const typeIcon = getTypeIcon(item.type);
            
            return `
                <div class="bulletin-item ${priorityClass}" data-priority="${item.priority}">
                    <div class="d-flex align-items-start">
                        <div class="bulletin-icon me-2">
                            <i class="bi ${typeIcon}"></i>
                        </div>
                        <div class="flex-grow-1">
                            <div class="bulletin-title">${escapeHtml(item.title)}</div>
                            <div class="bulletin-description">${escapeHtml(item.description)}</div>
                            <div class="bulletin-meta">
                                <span class="bulletin-course">${escapeHtml(item.course)}</span>
                                ${item.time_until ? `<span class="bulletin-time ms-2">${escapeHtml(item.time_until)}</span>` : ''}
                            </div>
                        </div>
                        ${item.priority === 'urgent' ? '<div class="bulletin-urgent-indicator"></div>' : ''}
                    </div>
                </div>
            `;
        }).join('');
        
        bulletinBoard.innerHTML = itemsHTML;
    }
    
    function getPriorityClass(priority) {
        switch (priority) {
            case 'urgent': return 'bulletin-urgent';
            case 'important': return 'bulletin-important';
            default: return 'bulletin-normal';
        }
    }
    
    function getTypeIcon(type) {
        switch (type) {
            case 'assignment': return 'bi-file-text';
            case 'exam': return 'bi-clipboard-check';
            case 'quiz': return 'bi-question-circle';
            case 'announcement': return 'bi-megaphone';
            default: return 'bi-info-circle';
        }
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Load bulletin board when page loads
    loadBulletinBoard();
    
    // Refresh bulletin board every 5 minutes
    setInterval(loadBulletinBoard, 5 * 60 * 1000);
    
    // Add refresh button functionality if exists
    const refreshBulletinBtn = document.getElementById('refresh-bulletin-btn');
    if (refreshBulletinBtn) {
        refreshBulletinBtn.addEventListener('click', function() {
            this.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i>';
            loadBulletinBoard().finally(() => {
                setTimeout(() => {
                    this.innerHTML = '<i class="bi bi-arrow-clockwise"></i>';
                }, 1000);
            });
        });
    }
});
