# LiveTrip Travel Review Platform

## Overview

LiveTrip is a full-stack travel review platform built with React, Express, and PostgreSQL. The application allows users to discover destinations, read and write reviews, and explore travel recommendations. It features a modern, responsive design with comprehensive search and filtering capabilities for hotels, restaurants, attractions, and experiences.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React with TypeScript using Vite for development and building
- **Routing**: Wouter for client-side routing with pages for home, search, destinations, and user profiles
- **State Management**: TanStack Query (React Query) for server state management and caching
- **Styling**: Tailwind CSS with shadcn/ui component library for consistent design
- **UI Components**: Radix UI primitives with custom styling for accessibility and consistency

### Backend Architecture
- **Framework**: Express.js with TypeScript running on Node.js
- **API Design**: RESTful API with endpoints for users, destinations, and reviews
- **Storage Layer**: Abstracted storage interface with in-memory implementation for development
- **Error Handling**: Centralized error handling middleware with structured error responses
- **Development**: Hot module replacement with Vite integration for seamless full-stack development

### Database Architecture
- **ORM**: Drizzle ORM for type-safe database operations
- **Schema**: PostgreSQL with three main tables (users, destinations, reviews) with proper foreign key relationships
- **Database Provider**: Neon serverless PostgreSQL configured for production deployment
- **Migrations**: Drizzle Kit for schema migrations and database management

### Key Features
- **Search & Discovery**: Advanced search with filters by category, rating, price range, and location
- **Review System**: Full CRUD operations for reviews with rating aggregation
- **User Profiles**: User management with profile pages showing review history
- **Responsive Design**: Mobile-first design with adaptive layouts
- **Type Safety**: End-to-end TypeScript with shared schema validation using Zod

## External Dependencies

### Core Dependencies
- **@neondatabase/serverless**: Neon PostgreSQL serverless driver for database connectivity
- **drizzle-orm**: Type-safe ORM with PostgreSQL dialect support
- **drizzle-zod**: Schema validation integration between Drizzle and Zod

### UI Framework
- **@radix-ui/***: Complete set of accessible UI primitives for complex components
- **tailwindcss**: Utility-first CSS framework with custom design tokens
- **class-variance-authority**: Type-safe variant handling for component styling
- **lucide-react**: Icon library for consistent iconography

### Frontend Libraries
- **@tanstack/react-query**: Server state management with caching and synchronization
- **wouter**: Lightweight routing library for React applications
- **date-fns**: Date utility library for formatting and manipulation
- **@hookform/resolvers**: Form validation integration with React Hook Form

### Development Tools
- **vite**: Fast build tool with hot module replacement
- **typescript**: Static type checking across the entire application
- **@replit/vite-plugin-***: Replit-specific development plugins for enhanced development experience