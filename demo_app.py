#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
HelloGitHub Demo Application

A comprehensive web-based demo that showcases the full functionality of HelloGitHub,
including content browsing, search, translation, and administrative tools.

Features:
- Browse HelloGitHub monthly issues
- Search projects by name, language, or description  
- Multi-language support (Chinese, English, Japanese)
- Content generation tools
- GitHub bot functionality demonstration
- Interactive project statistics
"""

import os
import re
import json
import glob
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
import markdown
from bs4 import BeautifulSoup

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hellogithub-demo-secret-key'

# Global data structures for caching
issues_cache = {}
projects_cache = []
stats_cache = {}

class HelloGitHubParser:
    """Parser for HelloGitHub markdown content"""
    
    def __init__(self, base_path):
        self.base_path = base_path
        self.content_path = os.path.join(base_path, 'content')
        
    def get_available_issues(self):
        """Get list of all available issues"""
        pattern = os.path.join(self.content_path, 'HelloGitHub*.md')
        files = glob.glob(pattern)
        issues = []
        
        for file_path in files:
            filename = os.path.basename(file_path)
            match = re.search(r'HelloGitHub(\d+)\.md', filename)
            if match:
                issue_num = int(match.group(1))
                issues.append({
                    'number': issue_num,
                    'filename': filename,
                    'path': file_path,
                    'language': 'zh'
                })
        
        # Sort by issue number
        issues.sort(key=lambda x: x['number'], reverse=True)
        return issues
    
    def parse_issue_content(self, issue_number, language='zh'):
        """Parse content from a specific issue"""
        if language == 'zh':
            file_path = os.path.join(self.content_path, f'HelloGitHub{issue_number:02d}.md')
        else:
            file_path = os.path.join(self.content_path, 'en', f'HelloGitHub{issue_number:02d}.md')
        
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.extract_projects_from_content(content, issue_number)
    
    def extract_projects_from_content(self, content, issue_number):
        """Extract project information from markdown content"""
        projects = []
        
        # Split content into sections
        sections = re.split(r'### ([^#\n]+)', content)
        
        current_category = "未分类"
        
        for i in range(1, len(sections), 2):
            if i + 1 < len(sections):
                category = sections[i].strip()
                section_content = sections[i + 1]
                
                # Extract projects from this section
                project_blocks = re.split(r'\n\d+、', '\n' + section_content)
                
                for block in project_blocks[1:]:  # Skip first empty element
                    project = self.parse_project_block(block, category, issue_number)
                    if project:
                        projects.append(project)
        
        return projects
    
    def parse_project_block(self, block, category, issue_number):
        """Parse individual project information"""
        lines = block.strip().split('\n')
        if not lines:
            return None
        
        # Extract project title and URL
        first_line = lines[0]
        
        # Look for markdown link pattern [title](url)
        link_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', first_line)
        if link_match:
            title = link_match.group(1)
            url = link_match.group(2)
        else:
            # Fallback: use first word as title
            title = first_line.split('：')[0] if '：' in first_line else first_line.split(':')[0]
            url = ""
        
        # Extract description (everything after first colon)
        description = ""
        if '：' in first_line:
            description = first_line.split('：', 1)[1].strip()
        elif ':' in first_line:
            description = first_line.split(':', 1)[1].strip()
        
        # Add remaining lines to description
        if len(lines) > 1:
            description += " " + " ".join(lines[1:])
        
        # Clean up description
        description = re.sub(r'<[^>]+>', '', description)  # Remove HTML tags
        description = re.sub(r'\!\[.*?\]\(.*?\)', '', description)  # Remove images
        description = description.strip()
        
        # Try to extract GitHub repo name
        github_repo = ""
        if 'github.com' in url:
            repo_match = re.search(r'github\.com/([^/]+/[^/?]+)', url)
            if repo_match:
                github_repo = repo_match.group(1)
        
        return {
            'title': title,
            'description': description,
            'url': url,
            'github_repo': github_repo,
            'category': category,
            'issue_number': issue_number,
            'language': self.detect_project_language(description + " " + title)
        }
    
    def detect_project_language(self, text):
        """Simple language detection based on keywords"""
        text_lower = text.lower()
        
        language_keywords = {
            'Python': ['python', 'django', 'flask', 'pandas', 'numpy'],
            'JavaScript': ['javascript', 'js', 'node', 'react', 'vue', 'angular'],
            'Java': ['java', 'spring', 'maven', 'gradle'],
            'Go': ['golang', 'go语言', ' go '],
            'Rust': ['rust', 'cargo'],
            'C++': ['c++', 'cpp'],
            'C': [' c语言', ' c '],
            'PHP': ['php', 'laravel'],
            'Ruby': ['ruby', 'rails'],
            'Swift': ['swift', 'ios'],
            'Kotlin': ['kotlin', 'android'],
            'TypeScript': ['typescript', 'ts'],
            'CSS': ['css', 'scss', 'sass'],
            'HTML': ['html'],
            'Shell': ['shell', 'bash', 'script'],
            'Docker': ['docker', 'dockerfile'],
            'Kubernetes': ['kubernetes', 'k8s']
        }
        
        for lang, keywords in language_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return lang
        
        return "其他"

def load_all_data():
    """Load all issue and project data into cache"""
    global issues_cache, projects_cache, stats_cache
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    parser = HelloGitHubParser(base_path)
    
    # Load issues
    issues = parser.get_available_issues()
    for issue in issues:
        projects = parser.parse_issue_content(issue['number'])
        if projects:
            issues_cache[issue['number']] = {
                'info': issue,
                'projects': projects
            }
            projects_cache.extend(projects)
    
    # Generate statistics
    stats_cache = generate_statistics()
    
    print(f"Loaded {len(issues_cache)} issues with {len(projects_cache)} total projects")

def generate_statistics():
    """Generate various statistics from the project data"""
    stats = {
        'total_projects': len(projects_cache),
        'total_issues': len(issues_cache),
        'projects_by_language': {},
        'projects_by_category': {},
        'projects_by_issue': {},
        'latest_issue': max(issues_cache.keys()) if issues_cache else 0
    }
    
    for project in projects_cache:
        # Language statistics
        lang = project.get('language', '其他')
        stats['projects_by_language'][lang] = stats['projects_by_language'].get(lang, 0) + 1
        
        # Category statistics  
        cat = project.get('category', '未分类')
        stats['projects_by_category'][cat] = stats['projects_by_category'].get(cat, 0) + 1
        
        # Issue statistics
        issue = project.get('issue_number', 0)
        stats['projects_by_issue'][issue] = stats['projects_by_issue'].get(issue, 0) + 1
    
    return stats

@app.route('/')
def index():
    """Main page showing overview and latest issues"""
    latest_issues = sorted(issues_cache.keys(), reverse=True)[:6]
    latest_projects = []
    
    for issue_num in latest_issues[:3]:
        if issue_num in issues_cache:
            projects = issues_cache[issue_num]['projects'][:3]  # Top 3 projects from each issue
            for project in projects:
                project['issue_number'] = issue_num
            latest_projects.extend(projects)
    
    return render_template('index.html', 
                         stats=stats_cache,
                         latest_issues=latest_issues,
                         latest_projects=latest_projects[:9])

@app.route('/browse')
def browse():
    """Browse all issues"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    all_issues = sorted(issues_cache.keys(), reverse=True)
    total = len(all_issues)
    start = (page - 1) * per_page
    end = start + per_page
    
    issues_page = all_issues[start:end]
    issues_data = []
    
    for issue_num in issues_page:
        issue_info = issues_cache[issue_num]['info']
        projects_count = len(issues_cache[issue_num]['projects'])
        issues_data.append({
            'number': issue_num,
            'projects_count': projects_count,
            'info': issue_info
        })
    
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'has_prev': page > 1,
        'has_next': page * per_page < total,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if page * per_page < total else None
    }
    
    return render_template('browse.html', issues=issues_data, pagination=pagination)

@app.route('/issue/<int:issue_number>')
def view_issue(issue_number):
    """View specific issue with all its projects"""
    if issue_number not in issues_cache:
        return render_template('error.html', message=f"Issue {issue_number} not found"), 404
    
    issue_data = issues_cache[issue_number]
    projects = issue_data['projects']
    
    # Group projects by category
    categories = {}
    for project in projects:
        cat = project.get('category', '未分类')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(project)
    
    return render_template('issue.html', 
                         issue_number=issue_number,
                         categories=categories,
                         total_projects=len(projects))

@app.route('/search')
def search():
    """Search projects"""
    query = request.args.get('q', '').strip()
    language = request.args.get('language', '')
    category = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    results = []
    
    if query or language or category:
        for project in projects_cache:
            # Text search
            if query:
                searchable_text = f"{project.get('title', '')} {project.get('description', '')}".lower()
                if query.lower() not in searchable_text:
                    continue
            
            # Language filter
            if language and project.get('language', '') != language:
                continue
            
            # Category filter
            if category and project.get('category', '') != category:
                continue
            
            results.append(project)
    
    # Pagination
    total = len(results)
    start = (page - 1) * per_page
    end = start + per_page
    results_page = results[start:end]
    
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'has_prev': page > 1,
        'has_next': page * per_page < total,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if page * per_page < total else None
    }
    
    # Get filter options
    languages = sorted(stats_cache['projects_by_language'].keys())
    categories = sorted(stats_cache['projects_by_category'].keys())
    
    return render_template('search.html',
                         results=results_page,
                         pagination=pagination,
                         query=query,
                         selected_language=language,
                         selected_category=category,
                         languages=languages,
                         categories=categories)

@app.route('/statistics')
def statistics():
    """Show project statistics and analytics"""
    return render_template('statistics.html', stats=stats_cache)

@app.route('/tools')
def tools():
    """Administrative tools and utilities"""
    return render_template('tools.html')

@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics data"""
    return jsonify(stats_cache)

@app.route('/api/search')
def api_search():
    """API endpoint for search functionality"""
    query = request.args.get('q', '').strip().lower()
    limit = request.args.get('limit', 10, type=int)
    
    results = []
    for project in projects_cache:
        if query in f"{project.get('title', '')} {project.get('description', '')}".lower():
            results.append(project)
            if len(results) >= limit:
                break
    
    return jsonify(results)

# Template functions
@app.template_filter('markdown')
def markdown_filter(text):
    """Convert markdown to HTML"""
    return markdown.markdown(text, extensions=['fenced_code'])

@app.template_filter('truncate_words')
def truncate_words(text, length=30):
    """Truncate text to specified number of words"""
    words = text.split()
    if len(words) <= length:
        return text
    return ' '.join(words[:length]) + '...'

if __name__ == '__main__':
    print("Loading HelloGitHub data...")
    load_all_data()
    print("Starting HelloGitHub Demo Application...")
    print("Visit http://localhost:5000 to see the demo")
    app.run(debug=True, host='0.0.0.0', port=5000)