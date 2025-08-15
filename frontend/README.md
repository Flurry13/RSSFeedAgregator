# RSS Feed Aggregator Frontend

A modern, responsive React frontend for the RSS Feed Aggregation and Translation System.

## Features

- 🎯 **Dashboard** - Overview with statistics and recent headlines
- 📰 **Feeds** - Browse and search through all collected headlines with filtering
- 🌍 **Translations** - Monitor translation status and manage the translation process
- 🔍 **Advanced Search** - Search by title, source, language, and more
- 📱 **Responsive Design** - Works perfectly on desktop, tablet, and mobile
- 🎨 **Modern UI** - Clean, intuitive interface built with Tailwind CSS

## Tech Stack

- **React 18** - Modern React with hooks
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **Lucide React** - Beautiful icons

## Getting Started

### Prerequisites

- Node.js 16+ 
- npm or yarn

### Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```

3. **Open your browser:**
   Navigate to `http://localhost:3000`

### Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   └── Header.tsx      # Navigation header
│   ├── context/            # React context providers
│   │   └── HeadlinesContext.tsx  # Headlines data management
│   ├── pages/              # Page components
│   │   ├── Dashboard.tsx   # Main dashboard
│   │   ├── Feeds.tsx       # Headlines browsing
│   │   └── Translations.tsx # Translation management
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # React entry point
│   └── index.css           # Global styles
├── public/                  # Static assets
├── package.json            # Dependencies and scripts
├── tailwind.config.js      # Tailwind CSS configuration
├── tsconfig.json           # TypeScript configuration
└── vite.config.ts          # Vite configuration
```

## API Integration

The frontend expects a backend API with the following endpoints:

- `GET /api/headlines` - Fetch all headlines
- `POST /api/translate` - Trigger headline translation

## Customization

### Styling
- Modify `tailwind.config.js` for theme customization
- Update `src/index.css` for global styles
- Use Tailwind utility classes for component styling

### Components
- Add new components in `src/components/`
- Create new pages in `src/pages/`
- Extend the context in `src/context/` for additional features

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint issues

### Code Quality

- TypeScript for type safety
- ESLint for code linting
- Prettier for code formatting (recommended)

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Follow the existing code style
2. Add TypeScript types for new features
3. Test on multiple screen sizes
4. Ensure accessibility standards are met

## License

This project is part of the RSS Feed Aggregator system. 