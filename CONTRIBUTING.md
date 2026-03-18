# Contributing to Digital Pulse

First off, thank you for considering contributing to Digital Pulse! 🎉

## 🚀 Quick Start for Contributors

1. **Fork** the repo
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/digital-pulse.git`
3. **Create branch**: `git checkout -b feature/your-feature-name`
4. **Make changes** and commit with clear messages
5. **Push**: `git push origin feature/your-feature-name`
6. **Submit PR** with description of changes

---

## 📋 Development Setup

### Prerequisites
- Node.js 18+
- Python 3.10+
- Git
- Supabase account

### Installation
```bash
# Backend
cd project
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

---

## 🎨 Code Standards

### Frontend (JavaScript/React)
- **Formatter**: Prettier
- **Linter**: ESLint
- **Naming**: camelCase for variables, PascalCase for components
- **Components**: Functional components with hooks
- **Memoization**: Use `useMemo`, `useCallback`, `React.memo` for performance
- **Comments**: Write clear JSDoc for complex functions

```javascript
// Good
const handleSubmit = useCallback(async (data) => {
  // Process submission
}, [dependencies]);

// Avoid
function handleSubmit(data) {
  // Inline function recreated every render
}
```

### Backend (Python)
- **Formatter**: Black
- **Linter**: Flake8
- **Type Hints**: Required for all functions
- **Docstrings**: Google style
- **Async**: Use async/await for I/O operations

```python
# Good
async def fetch_posts(limit: int = 50) -> List[Post]:
    """
    Fetch posts from database with limit.

    Args:
        limit: Maximum number of posts to fetch

    Returns:
        List of Post objects
    """
    return await db.posts.select().limit(limit)
```

---

## 🧪 Testing

### Frontend Tests
```bash
cd frontend
npm run test
```

### Backend Tests
```bash
pytest tests/ -v --cov=backend
```

### Write Tests For:
- ✅ New API endpoints
- ✅ New components
- ✅ Data processing functions
- ✅ Error handling
- ✅ Edge cases

---

## 📝 Commit Message Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code restructuring
- `perf`: Performance improvement
- `test`: Adding tests
- `chore`: Maintenance tasks

### Examples
```bash
feat(dashboard): add regional heatmap component

- Implemented D3.js-based heatmap
- Added color gradient based on engagement
- Optimized for mobile view

Closes #45

---

fix(api): resolve clustering timeout for large datasets

- Added pagination to reduce memory usage
- Implemented background task for clustering
- Cache results for 5 minutes

Fixes #78
```

---

## 🐛 Bug Reports

### Before Submitting
1. Check existing issues
2. Verify it's reproducible
3. Check if it's already fixed in latest version

### Bug Report Template
```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
- OS: [e.g. Windows 11]
- Browser: [e.g. Chrome 120]
- Version: [e.g. 1.0.0]

**Console Logs**
Paste relevant console output.
```

---

## 💡 Feature Requests

### Feature Request Template
```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Any alternative solutions you've thought about.

**Additional context**
Mockups, examples, etc.

**Complexity Estimate**
- Simple (< 1 day)
- Medium (1-3 days)
- Complex (> 3 days)
```

---

## 🔄 Pull Request Process

### Before Submitting PR
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] No console.log statements (use proper logging)
- [ ] Build succeeds without warnings

### PR Template
```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change
- [ ] Documentation update

## Testing
Describe how you tested this.

## Screenshots (if applicable)
Add screenshots here.

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests added
- [ ] Documentation updated
```

---

## 🏗️ Project Architecture

### Adding New Component (Frontend)
1. Create component in `frontend/components/`
2. Use functional component with hooks
3. Wrap in `React.memo` for performance
4. Export as default
5. Import in parent component

### Adding New API Endpoint (Backend)
1. Create router in `backend/api/`
2. Add route function with type hints
3. Update `main.py` to include router
4. Add tests in `tests/api/`
5. Update API documentation

### Adding New Scraper
1. Create scraper in `backend/scrapers/`
2. Implement `async def scrape()` method
3. Add scheduling in pipeline
4. Handle errors gracefully
5. Add rate limiting

---

## 📊 Performance Guidelines

### Frontend
- Keep components small and focused
- Use `useMemo` for expensive calculations
- Avoid inline function definitions in render
- Limit data displayed (pagination/virtualization)
- Lazy load heavy components

### Backend
- Use async/await for I/O
- Implement caching strategically
- Add database indexes
- Batch database operations
- Monitor query performance

---

## 🚨 Security Best Practices

### Frontend
- ❌ Never commit API keys
- ✅ Validate all user input
- ✅ Sanitize displayed data
- ✅ Use environment variables
- ✅ Implement CORS properly

### Backend
- ❌ Never commit secrets
- ✅ Use environment variables
- ✅ Validate request payloads
- ✅ Implement rate limiting
- ✅ Use parameterized queries
- ✅ Hash sensitive data

---

## 📚 Resources

### Learn More
- [React Docs](https://react.dev/)
- [Next.js Docs](https://nextjs.org/docs)
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/)
- [BERTopic Guide](https://maartengr.github.io/BERTopic/)

### Tools
- [React DevTools](https://react.dev/learn/react-developer-tools)
- [FastAPI Swagger UI](http://localhost:8000/docs)
- [Supabase Dashboard](https://app.supabase.com/)

---

## 💬 Community

### Communication Channels
- **Discord**: [Join our server](https://discord.gg/digitalpulse)
- **GitHub Discussions**: Ask questions, share ideas
- **Email**: dev@digitalpulse.io

### Code of Conduct
- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Follow project guidelines

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## 🎯 Priority Areas for Contribution

We're especially looking for help with:

### High Priority
- [ ] Real-time WebSocket implementation
- [ ] Advanced sentiment analysis
- [ ] Mobile responsive improvements
- [ ] Additional data source integrations

### Medium Priority
- [ ] Unit test coverage improvements
- [ ] Documentation enhancements
- [ ] Performance optimizations
- [ ] Accessibility improvements

### Good First Issues
- [ ] Fix typos in documentation
- [ ] Add missing TypeScript types
- [ ] Improve error messages
- [ ] Add loading states

---

## 🙏 Thank You!

Every contribution, no matter how small, makes a difference. Thank you for helping make Digital Pulse better! 🚀

**Questions?** Open a [GitHub Discussion](https://github.com/YOUR_USERNAME/digital-pulse/discussions) or reach out on Discord.
